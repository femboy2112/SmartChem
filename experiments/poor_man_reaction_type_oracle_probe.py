"""POOR-MAN-REACTION-TYPE-ORACLE-01 (R56): the FIRST sound production code the ingenuity reward ships --
a reaction-TYPE oracle that DEMOTES reaction-TYPE fictions off the affordability frontier.

THE ARC.  R49-R55 all DEFERRED the ingenuity reward's soundness gate: every attempt was a bounded-radius LOCAL
recognizer trying to CARRY an unbounded property (feasibility, then type-validity) via a decision function
``valid = g(f(step))``, and every one collided (the R55 theorem: a bounded feature is shared by some real and some
fake step).  R55 also PROVED the consumer: the production affordability frontier ships ~72% reaction-TYPE FICTIONS
(Problem A: a step that is no real reaction at all) with EMPTY ``hard_blockers``.

THE ESCAPE (this round).  A POSITIVE WHITELIST of attested reaction-class recognizers
(:mod:`smartchem.experiment.reaction_type_oracle`), wired as a fail-closed demoter into
``service._affordability_frontier`` (a sibling to ``route_catalyst_blockers``).  A step is VOUCHED iff it
POSITIVELY matches a known reaction class; otherwise it is demoted as *"unrecognized reaction type"* -- honest
non-recognition, NOT the claim "proven fake".  The unbounded-ness surfaces as COVERAGE LOSS (a real-but-unregistered
reaction is demoted-as-unrecognized), NEVER a false-VOUCH -- genuinely different-in-kind from escape #7.

SCOPE: ACYL-condensation ONLY (esterification/amidation), the one recognizer with a conservation-lock proof (a fired
step is FORCED by formula conservation within the elementary shape onto a real acyl transfer; R48-hardened).  A
GENERAL "new C-N bond" recognizer FAILS the admission gate -- it fires on BOTH caffeine N-methylation (real) AND
aromatic phenol->aniline amination (fake), the R55 theorem one alphabet over -- so it is NOT shipped, and the R45
caffeine genericity win is demoted as honest coverage loss this round (recoverable only behind a class-specific
conservation-locked recognizer, never a bounded-radius patch).

THIS PROBE FREEZES, against LIVE code: (1) the consumer SERVED (isopentyl acetate's 10 frontier fictions now all
carry the reaction-type blocker, was 0); (2) ZERO false-VOUCH across the whole production frontier + non-vacuity
(genuine acyl reals still vouched); (3) both R55 false-VOUCH fakes now DEMOTED; (4) the R55 false-EXCLUDE reals
demoted-as-unrecognized (the designed, honest coverage loss); (5) the escape-#7 BOUNDARY (the general N-C recognizer
collides -> why acyl-only); (6) FAIL-CLOSED totality (a raising recognizer never yields a spurious VOUCH).

R57 UPDATE (hash re-frozen 98cceeeb -> fc8fea1e): this probe measures the LIVE oracle, and R57 added a second
conservation-locked recognizer (dehydrative etherification, :func:`smartchem.experiment.feasibility._is_intermolecular_etherification`).
The whole-frontier soundness measurement here therefore grew by ONE genuine real -- ``dimethyl ether`` (2 methanol ->
dimethyl ether + water) is now VOUCHED as an etherification -- so ``reals_vouched`` went 4 -> 5 and ``vouched_targets``
gained "dimethyl ether".  ``false_vouch_count`` stays 0 and every R56 SHIP assertion still holds; only the vouched-set
count moved, so the frozen hash is re-frozen to the post-R57 truth (the R55->R56 supersession pattern).  R57's own
etherification behaviour is pinned by :mod:`experiments.poor_man_etherification_recognizer_probe`.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.structure import structure_by_name, registered_structures
from smartchem.smiles import parse_smiles
from smartchem.experiment.compile import compile_synthesis
from smartchem.service import build_recompile_request, run_compilation, _reconstruct_route
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type

# reuse the R55 probe's helpers + its adversarial case tables (the C-C rule is our ground-truth fiction LABEL here)
from experiments.poor_man_step_validity_demoter_defer_probe import (
    _resolve, _routes_of, raw_rule_blocks, _FALSE_VOUCHES, _FALSE_EXCLUDES,
)

FROZEN_HASH = "fc8fea1eaa7b6c110775580e5a20f9b02ef610fd067f84903c86a7f1fb4f88e3"


def _routes(tsmi, avail, reags=None):
    tgt = parse_smiles(tsmi)
    av = tuple(_resolve(t) for t in avail)
    kw = {"available": av, "commodities": ()}
    if reags is not None:
        kw["reagents"] = tuple(_resolve(t) for t in reags)
    return _routes_of(compile_synthesis(tgt, **kw))


def _demotes(route) -> bool:
    return bool(route_reaction_type_blockers(route))


def _vouches(route) -> bool:
    return not route_reaction_type_blockers(route)


def _is_water(m) -> bool:
    return m.charge == 0 and dict(m.formula) == {"H": 2, "O": 1}


def _general_nc_recognizer(step) -> bool:
    """The GENERAL 'new N-C single bond within the elementary shape' recognizer -- the one that FAILS the
    conservation-lock admission gate.  Frozen here ONLY to prove the collision that justifies NOT shipping it."""
    nwr = [m for m in step.reactants if not _is_water(m)]
    nwp = [m for m in step.products if not _is_water(m)]
    if len(nwr) != 2 or len(nwp) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False

    def nc(m):
        els = m.atoms
        return sum(1 for b in m.bonds if {els[b.i], els[b.j]} == {"N", "C"} and b.order == 1)
    return (sum(nc(m) for m in step.products) - sum(nc(m) for m in step.reactants)) > 0


# --------------------------------------------------------------------------------------------------
# (1) THE CONSUMER SERVED: isopentyl acetate's frontier fictions now carry the reaction-type blocker.
# --------------------------------------------------------------------------------------------------
def consumer_served() -> dict:
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    fr = resp.affordability_frontier
    rt_blocked = sum(
        1 for e in fr
        if any("unrecognized reaction type" in b for b in ((getattr(e.cost_vector, "hard_blockers", ()) or ()) + (getattr(e.cost_vector, "fiction_blockers", ()) or ())))
    )
    return {
        "target": "isopentyl acetate",
        "frontier_entries": len(fr),
        "reaction_type_blocked": rt_blocked,
        "all_blocked": rt_blocked == len(fr) and len(fr) > 0,
    }


# --------------------------------------------------------------------------------------------------
# (2) SOUNDNESS + NON-VACUITY: over the whole production frontier, cross-tab the oracle vs the R55 C-C
#     fiction label.  FALSE-VOUCH (oracle vouches a C-C fiction) MUST be 0; genuine acyl reals stay vouched.
# --------------------------------------------------------------------------------------------------
def soundness_and_coverage() -> dict:
    tp = fp = tn = fn = total = 0
    vouched_targets: set[str] = set()
    for ns in registered_structures():
        try:
            resp = run_compilation(build_recompile_request(ns.name, max_depth=3))
        except Exception:
            continue
        for d in getattr(resp, "ranked_route_dossiers", ()) or ():
            try:
                r = _reconstruct_route(d.replay_payload)
            except Exception:
                continue
            total += 1
            is_fiction = raw_rule_blocks(r)     # R55 ground-truth label: forms a C-C bond => reaction-type fiction
            vouch = _vouches(r)
            if vouch and not is_fiction:
                tn += 1
                vouched_targets.add(ns.name)
            elif vouch and is_fiction:
                fp += 1                          # FALSE-VOUCH -- the catastrophic error; must be 0
            elif (not vouch) and is_fiction:
                tp += 1                          # correctly demoted a fiction
            else:
                fn += 1                          # a (raw-label) real demoted-as-unrecognized: honest coverage loss
    return {
        "total_frontier_routes": total,
        "fictions_demoted": tp,
        "false_vouch_count": fp,
        "reals_vouched": tn,
        "reals_coverage_loss": fn,
        "vouched_targets": sorted(vouched_targets),
    }


# --------------------------------------------------------------------------------------------------
# (3)+(4) THE R55 CASES: both false-VOUCH fakes now DEMOTED; the false-EXCLUDE reals demoted-as-unrecognized.
# --------------------------------------------------------------------------------------------------
def r55_fakes_now_demoted() -> list:
    rows = []
    for tsmi, avail, desc, _why in _FALSE_VOUCHES:
        rs = _routes(tsmi, avail)
        rows.append({"case": desc, "reachable": bool(rs), "demoted": bool(rs) and all(_demotes(r) for r in rs)})
    return rows


def r55_reals_coverage_loss() -> list:
    rows = []
    for tsmi, avail, reags, desc, _why in _FALSE_EXCLUDES:
        rs = _routes(tsmi, avail, reags=reags)
        rows.append({
            "case": desc, "reachable": bool(rs),
            "demoted_as_unrecognized": bool(rs) and all(_demotes(r) for r in rs),
        })
    return rows


# --------------------------------------------------------------------------------------------------
# (5) THE ESCAPE-#7 BOUNDARY: the general N-C recognizer COLLIDES -> the acyl-only scope is principled.
#     And the shipped (acyl-only) oracle DEMOTES caffeine as honest coverage loss (never false-vouches it).
# --------------------------------------------------------------------------------------------------
def escape7_boundary() -> dict:
    caff = _routes("Cn1cnc2c1c(=O)n(C)c(=O)n2C", ["theobromine", "methanol"], reags=["water"])
    if not caff:
        caff = _routes_of(compile_synthesis(structure_by_name("caffeine").molecule, max_depth=2))
    amin = _routes("Nc1ccc(N)cc1", ["ammonia", "4-aminophenol"])
    caff_nc = bool(caff) and any(any(_general_nc_recognizer(st) for st in r.steps) for r in caff)
    amin_nc = bool(amin) and any(any(_general_nc_recognizer(st) for st in r.steps) for r in amin)
    return {
        "general_nc_fires_caffeine": caff_nc,             # must-vouch, the general recognizer fires
        "general_nc_fires_amination_fake": amin_nc,       # must-NOT-vouch, but the general recognizer fires too
        "collision": caff_nc and amin_nc,                 # => the general N-C recognizer IS escape #7 -> not shipped
        # the SHIPPED acyl-only oracle: caffeine is demoted as HONEST coverage loss, never false-vouched
        "shipped_oracle_vouches_caffeine": bool(caff) and any(_vouches(r) for r in caff),
        "shipped_oracle_demotes_caffeine": bool(caff) and all(_demotes(r) for r in caff),
    }


# --------------------------------------------------------------------------------------------------
# (6) FAIL-CLOSED TOTALITY: a recognizer that RAISES is treated as abstaining -- never a spurious VOUCH,
#     and never a crash (the frontier build is outside the compile path's ScissionError guard).
# --------------------------------------------------------------------------------------------------
def fail_closed_on_recognizer_error() -> dict:
    import smartchem.experiment.reaction_type_oracle as O
    orig = O._RECOGNIZERS

    def _boom(step):
        raise RuntimeError("recognizer boom")

    O._RECOGNIZERS = (("boom", _boom),) + orig
    try:
        # a fake step, with a raising recognizer prepended: recognize_reaction_type must NOT crash, and the fake
        # must STILL be demoted (the raising recognizer abstains; no spurious vouch).
        rs = _routes("CC(C)CCO", ["CC(C)CC", "hydrogen peroxide"])  # the R55 H2O2 hydroxylation fake
        no_crash = True
        try:
            for r in rs:
                for st in r.steps:
                    recognize_reaction_type(st)
        except Exception:
            no_crash = False
        still_demoted = bool(rs) and all(_demotes(r) for r in rs)
    finally:
        O._RECOGNIZERS = orig
    return {"no_crash_on_raising_recognizer": no_crash, "fake_still_demoted": still_demoted}


def _payload() -> dict:
    consumer = consumer_served()
    sc = soundness_and_coverage()
    fakes = r55_fakes_now_demoted()
    reals = r55_reals_coverage_loss()
    esc = escape7_boundary()
    fc = fail_closed_on_recognizer_error()
    return {
        "schema": "poor-man-reaction-type-oracle-01",
        "round": 56,
        "consumer_served": consumer,
        "soundness_and_coverage": sc,
        "r55_fakes_now_demoted": fakes,
        "r55_reals_coverage_loss": reals,
        "escape7_boundary": esc,
        "fail_closed": fc,
        # THE VERDICT: R56 SHIPS the first sound production code for the ingenuity reward.  The oracle is a positive
        # whitelist (different-in-kind from escape #7): 0 false-VOUCH across the frontier, non-vacuous (genuine acyl
        # reals still vouched), it SERVES the proven consumer (isopentyl acetate's fictions all demoted), it demotes
        # both R55 fakes, and its coverage loss (FC/Claisen/caffeine) is honest non-recognition -- while the general
        # N-C recognizer (escape #7) is proven-collided and deliberately not shipped.
        "ship_verdict": (
            consumer["all_blocked"]
            and sc["false_vouch_count"] == 0
            and sc["reals_vouched"] >= 1
            and all(f["demoted"] for f in fakes if f["reachable"])
            and esc["collision"] is True
            and esc["shipped_oracle_vouches_caffeine"] is False
            and fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R56 SHIP result holds against live code: the consumer is served (all isopentyl-acetate frontier
    entries now reaction-type-blocked), the oracle is SOUND (0 false-VOUCH across the production frontier) and
    NON-VACUOUS (genuine acyl reals vouched), both R55 fakes are demoted, the escape-#7 boundary holds (the general
    N-C recognizer collides, so acyl-only is principled; the shipped oracle never false-vouches caffeine), and the
    demoter is fail-closed and total (a raising recognizer never yields a spurious VOUCH or a crash)."""
    p = _payload()
    c = p["consumer_served"]
    sc = p["soundness_and_coverage"]
    assert c["all_blocked"], f"consumer not served (frontier fictions not all blocked): {c}"
    assert sc["false_vouch_count"] == 0, f"UNSOUND: the oracle false-VOUCHed a reaction-type fiction: {sc}"
    assert sc["reals_vouched"] >= 1, f"VACUOUS: no genuine real reaction survived the oracle: {sc}"
    assert all(f["demoted"] for f in p["r55_fakes_now_demoted"] if f["reachable"]), \
        f"an R55 false-VOUCH fake is not demoted by the oracle: {p['r55_fakes_now_demoted']}"
    assert p["escape7_boundary"]["collision"] is True, \
        f"the general N-C recognizer stopped colliding -- re-audit the acyl-only scope: {p['escape7_boundary']}"
    assert p["escape7_boundary"]["shipped_oracle_vouches_caffeine"] is False, \
        f"the shipped oracle FALSE-VOUCHED caffeine (should be honest coverage loss): {p['escape7_boundary']}"
    assert p["fail_closed"]["no_crash_on_raising_recognizer"] and p["fail_closed"]["fake_still_demoted"], \
        f"fail-closed totality broken: {p['fail_closed']}"
    assert p["ship_verdict"], f"R56 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
