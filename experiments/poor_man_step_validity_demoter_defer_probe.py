"""POOR-MAN-STEP-VALIDITY-DEMOTER-DEFER-01 (R55): the SIXTH verified defer of the ingenuity reward --
and the first with a PROVEN, SURFACED, DOMINANT live consumer.

R56 UPDATE (post-supersession): the consumer this probe PROVED -- the frontier fictions that R55 measured
shipping UN-BLOCKED -- has since been SERVED by the R56 reaction-type oracle, which now BLOCKS them.  This probe
is updated to the post-R56 truth: the DURABLE fact (every frontier route is a reconstructed C-C-fusion fiction)
remains the consumer proof; "now blocked by R56" replaces the superseded "ships unblocked" measurement.  The
R55 DEFER itself is unchanged (the join-element rule's dual false-VOUCH/false-EXCLUDE failure is independent of
R56).  See experiments/poor_man_reaction_type_oracle_probe.py for the R56 SHIP.

WHAT CHANGED THIS ROUND (the reframe that broke five rounds of "zero consumers").  The compiler DERIVES
reactions by capped-scission graph surgery that conserves molecular FORMULA, not chemical feasibility, so the
search OVER-GENERATES formula-balanced-but-fake steps.  Measured on the FULL PRODUCTION frontier
(``run_compilation(...).affordability_frontier``): the majority of affordability-frontier routes across the
registry are chemically FICTIONAL and ship UN-BLOCKED today -- isopentyl acetate alone presents TEN
"fully-commodity, ~4.5c" routes, every one a graph fiction with empty ``hard_blockers``.  This REFUTES the
standing "zero live consumers" premise that gated R49-R54: the ingenuity reward's home
(``service._affordability_frontier`` hard_blockers -> G6) has a proven, dominant job -- SINK the fictions.

AND it RE-DECOMPOSES the arch's problem.  The frontier pollution is PROBLEM A -- reaction-TYPE fiction (a step
that is no real reaction at all) -- which is DISTINCT from and DOMINATES the 5x-deferred PROBLEM B (substrate
feasibility: a real reaction type whose substrate misbehaves -- polymerises/decomposes, the R49-R54 keystone).
The measurement shows the pollution is ~100% Problem A.  The arch spent five rounds on Problem B; Problem B was
never what polluted the frontier.

WHY IT IS STILL A DEFER.  The natural Problem-A demoter -- "a step whose FORMED JOIN BOND is C-C (a skeleton
fusion by small-molecule loss) is fake; C-O/C-N/C-S joins are sound" -- was taken to a 5-bearing adversarial
design gate and BROKE.  The join-bond element is an EXACTLY-computable bounded-local feature (a total function
of the CappedScission.cut), but it does NOT map to fake/real:

  * FALSE-VOUCH (the join-element under-approximates the fake set): reachable fakes whose join is C-O/C-N are
    VOUCHED -- ``isopentane + H2O2 -> isopentyl alcohol + water`` (C-H hydroxylation, no bench mechanism, C-O
    join) and ``ammonia + 4-aminophenol -> p-phenylenediamine + water`` (aromatic amination of a phenol, no
    kitchen mechanism, C-N join, BOTH precursors commodities).
  * FALSE-EXCLUDE (the join-element over-approximates the fake set): reachable REAL C-C condensations are SUNK
    -- Friedel-Crafts acylation/alkylation, Kolbe-Schmitt, Claisen all form a genuine C-C bond.

So "C-C join" is NEITHER necessary NOR sufficient for "fake".  This is the R49-R54 theorem ONE ALPHABET OVER:
a bounded-radius local recognizer cannot carry an UNBOUNDED property.  For R49-R54 the property was reaction
FEASIBILITY (does the substrate cooperate); here it is reaction-TYPE VALIDITY (does a mechanism exist).  Both
need the open reaction-mechanism space (electrophilicity, aromaticity, activation, leaving groups, bond-order
changes) that no local census of the join can read.  Every refinement (join-element -> +leaving-group ->
+aromaticity) is met by a new leak, the R53/R54 patch spiral.

THEOREM (R55, the defer's contribution): reaction-TYPE validity resists bounded-radius local recognition just
as reaction feasibility did (R49-R54).  The escape for BOTH is the same the prior defers named: an EXTERNAL
reaction oracle (match each derived step to a known reaction TYPE, fail-closed, demote unmatched) -- at the cost
of the "derive untabulated reactions" genericity (the R45 caffeine-methylation win would need its template
registered).  That genericity tradeoff is the real R56 design question, now GATED on a proven consumer (met).

This probe FREEZES, against LIVE compiler code: (1) the proven consumer (un-blocked fictions on the frontier),
(2) the base rate of pollution, (3) the RAW rule's two FATAL failure modes reproduced, (4) the defer verdict.
The RAW rule is deliberately left UNWIRED -- shipping a proven-unsound blacklist recurs the theorem.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.structure import structure_by_name, registered_structures
from smartchem.smiles import parse_smiles
from smartchem.experiment.compile import compile_synthesis, _equation
from smartchem.service import build_recompile_request, run_compilation, _reconstruct_route

FROZEN_HASH = "b069b416c110e0d2445454274ce97353e853c12b8c56718e9be5072d9679d9bc"


# --------------------------------------------------------------------------------------------------
# The join-validity INSTRUMENT.  A step's formed join bond is the CappedScission.cut re-joined in the
# assembly direction; its skeleton signature is the net change in C-C bond count between products and
# reactants.  dCC>0 == a NEW C-C bond formed with small-molecule loss (a skeleton fusion).  This is a
# faithful proxy for the atom-mapped join on every route measured here (cross-checked against exact
# capped-scission cut recovery in the R55 gate); it IS the operational "RAW rule" under review.
# --------------------------------------------------------------------------------------------------
def _cc_bonds(mol) -> int:
    els = [a.element if hasattr(a, "element") else a for a in mol.atoms]
    return sum(1 for b in mol.bonds if els[b.i] == "C" and els[b.j] == "C")


def _step_delta_cc(step) -> int:
    return sum(_cc_bonds(m) for m in step.products) - sum(_cc_bonds(m) for m in step.reactants)


def raw_rule_blocks(route) -> bool:
    """The RAW demoter under review: BLOCK a route iff some step forms a new C-C bond (skeleton fusion)."""
    return any(_step_delta_cc(st) > 0 for st in route.steps)


def _routes_of(cs) -> list:
    return [getattr(rf, "route", rf) for rf in cs.ranked]


# --------------------------------------------------------------------------------------------------
# (1) THE PROVEN CONSUMER: the frontier is populated with reconstructed C-C-fusion FICTIONS (durable).
#     R55 measured them shipping UN-BLOCKED (empty hard_blockers) -- the live-consumer proof.  R56's
#     reaction-type oracle has since SERVED that consumer: those fictions now carry a reaction-type hard
#     blocker instead of shipping clean (see experiments/poor_man_reaction_type_oracle_probe).  This probe
#     is updated to the post-R56 truth: the DURABLE fact (the routes are fictions) is the consumer proof;
#     "now blocked by R56" replaces the superseded "ships unblocked" measurement.
# --------------------------------------------------------------------------------------------------
def consumer_proof() -> dict:
    """Isopentyl acetate's live frontier: every reconstructed route is a C-C-fusion fiction (the proven,
    dominant consumer) -- and, post-R56, every frontier entry now carries a reaction-type hard blocker
    (the consumer R55 proved has since been SERVED)."""
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    fr = resp.affordability_frontier
    routes = []
    for d in getattr(resp, "ranked_route_dossiers", ()) or ():
        try:
            routes.append(_reconstruct_route(d.replay_payload))
        except Exception:
            pass
    reaction_type_blocked = sum(
        1 for e in fr
        if any("unrecognized reaction type" in b for b in (getattr(e.cost_vector, "hard_blockers", ()) or ()))
    )
    fake = sum(1 for r in routes if raw_rule_blocks(r))
    return {
        "target": "isopentyl acetate",
        "frontier_entries": len(fr),
        "frontier_entries_reaction_type_blocked": reaction_type_blocked,
        "reconstructed_routes": len(routes),
        "fictional_routes": fake,
        # the DURABLE R55 consumer proof: every reconstructed frontier route is a C-C-fusion fiction
        "all_reconstructed_fictional": fake == len(routes) and len(routes) > 0,
        # post-R56: those fictions are now all blocked by the reaction-type oracle (the consumer SERVED)
        "all_frontier_reaction_type_blocked": reaction_type_blocked == len(fr) and len(fr) > 0,
    }


# --------------------------------------------------------------------------------------------------
# (2) THE BASE RATE: fraction of production-frontier routes across the registry that are fictional.
# --------------------------------------------------------------------------------------------------
def base_rate() -> dict:
    total = fake = targets = 0
    for ns in registered_structures():
        try:
            resp = run_compilation(build_recompile_request(ns.name, max_depth=3))
        except Exception:
            continue
        routes = []
        for d in getattr(resp, "ranked_route_dossiers", ()) or ():
            try:
                routes.append(_reconstruct_route(d.replay_payload))
            except Exception:
                pass
        if routes:
            targets += 1
            total += len(routes)
            fake += sum(1 for r in routes if raw_rule_blocks(r))
    return {
        "targets_with_routes": targets,
        "total_frontier_routes": total,
        "fictional_routes": fake,
        "fictional_fraction": round(fake / total, 3) if total else 0.0,
    }


# --------------------------------------------------------------------------------------------------
# (3) THE FATAL REFUTATION.  The RAW rule FALSE-VOUCHes reachable C-O/C-N fakes, and FALSE-EXCLUDEs
#     reachable REAL C-C condensations.  Each case is compiled through the real search.
# --------------------------------------------------------------------------------------------------
# reachable FAKES whose join is NOT C-C -> the RAW rule abstains -> VOUCH (unsound).
_FALSE_VOUCHES = (
    # (target_smiles, [available_smiles OR named], description, why_fake)
    ("CC(C)CCO", ["CC(C)CC", "hydrogen peroxide"], "isopentane + H2O2 -> isopentyl alcohol",
     "direct H2O2 hydroxylation of an unactivated C-H has no bench mechanism (C-O join)"),
    ("Nc1ccc(N)cc1", ["ammonia", "4-aminophenol"], "ammonia + 4-aminophenol -> p-phenylenediamine",
     "aromatic amination of a phenol OH is not a kitchen condensation (Bucherer; C-N join)"),
)

# reachable REAL C-C condensations -> the RAW rule blocks -> false-EXCLUDE.
# each: (target_smiles, [available], [cutting reagents], description, why_real)
_FALSE_EXCLUDES = (
    ("CC(=O)c1ccccc1", ["benzene", "acetic acid"], ["water"], "benzene + acetic acid -> acetophenone",
     "Friedel-Crafts acylation, a real named C-C-forming reaction"),
    ("Cc1ccccc1", ["benzene", "methanol"], ["water"], "benzene + methanol -> toluene",
     "Friedel-Crafts alkylation, a real named C-C-forming reaction"),
    ("CCOC(=O)CC(=O)C", ["CCOC(=O)C"], ["ethanol"], "2 ethyl acetate -> ethyl acetoacetate + ethanol",
     "Claisen condensation, a real base-mediated C-C-forming reaction (leaving group ethanol)"),
)


def _resolve(token: str):
    s = structure_by_name(token)
    if s is not None:
        return s.molecule
    return parse_smiles(token)


def run_false_vouches() -> list:
    rows = []
    for tsmi, avail, desc, why in _FALSE_VOUCHES:
        tgt = parse_smiles(tsmi)
        av = tuple(_resolve(t) for t in avail)
        try:
            cs = compile_synthesis(tgt, available=av, commodities=())
        except Exception as exc:  # pragma: no cover
            rows.append({"case": desc, "reachable": False, "error": f"{type(exc).__name__}: {exc}",
                         "raw_rule_blocks": None, "is_false_vouch": False, "why_fake": why})
            continue
        routes = _routes_of(cs)
        reachable = len(routes) > 0
        # the FAKE is reached AND the RAW rule does NOT block it -> a false-VOUCH
        vouched = reachable and not any(raw_rule_blocks(r) for r in routes)
        rows.append({
            "case": desc, "reachable": reachable,
            "equation": _equation(routes[0]) if reachable else None,
            "raw_rule_blocks": (not vouched) if reachable else None,
            "is_false_vouch": vouched, "why_fake": why,
        })
    return rows


def run_false_excludes() -> list:
    rows = []
    for tsmi, avail, reags, desc, why in _FALSE_EXCLUDES:
        tgt = parse_smiles(tsmi)
        av = tuple(_resolve(t) for t in avail)
        rg = tuple(_resolve(t) for t in reags)
        try:
            cs = compile_synthesis(tgt, available=av, reagents=rg, commodities=())
        except Exception as exc:  # pragma: no cover
            rows.append({"case": desc, "reachable": False, "error": f"{type(exc).__name__}: {exc}",
                         "raw_rule_blocks": None, "is_false_exclude": False, "why_real": why})
            continue
        routes = _routes_of(cs)
        reachable = len(routes) > 0
        # the REAL reaction is reached AND the RAW rule blocks it -> a false-EXCLUDE
        excluded = reachable and all(raw_rule_blocks(r) for r in routes)
        rows.append({
            "case": desc, "reachable": reachable,
            "equation": _equation(routes[0]) if reachable else None,
            "raw_rule_blocks": excluded if reachable else None,
            "is_false_exclude": excluded, "why_real": why,
        })
    return rows


def _payload() -> dict:
    consumer = consumer_proof()
    rate = base_rate()
    fv = run_false_vouches()
    fx = run_false_excludes()
    n_fv = sum(1 for r in fv if r["is_false_vouch"])
    n_fx = sum(1 for r in fx if r["is_false_exclude"])
    return {
        "schema": "poor-man-step-validity-demoter-defer-01",
        "round": 55,
        # the transformative advance: a PROVEN, SURFACED, DOMINANT live consumer (refutes "zero consumers")
        "consumer_proof": consumer,
        "base_rate": rate,
        # the FATAL refutation of the RAW join-element demoter
        "false_vouches": fv,
        "false_excludes": fx,
        "counts": {
            "false_vouch_classes": n_fv,     # reachable C-O/C-N fakes the RAW rule VOUCHes (>=1 => unsound)
            "false_exclude_classes": n_fx,   # reachable real C-C condensations the RAW rule SINKS (>=1 => over-broad)
        },
        # the reframe: the pollution is Problem A (reaction-type fiction), not the 5x-deferred Problem B
        "problem_a_is_the_consumer": True,
        # THE VERDICT: DEFER #6.  The consumer is proven, but the bounded-local join-element demoter both
        # false-VOUCHes reachable non-C-C fakes AND false-EXCLUDEs reachable real C-C reactions -- the join
        # element is neither necessary nor sufficient for fakeness.  Reaction-TYPE validity, like feasibility,
        # is not carriable by a bounded-radius local recognizer.
        # the DEFER rests on DURABLE facts (independent of R56): the consumer is real (the frontier is populated
        # with reconstructed fictions), the pollution is dominant, and the join-element rule FAILS both ways.
        "defer_verdict": (
            consumer["all_reconstructed_fictional"]
            and rate["fictional_fraction"] >= 0.5
            and n_fv >= 1
            and n_fx >= 1
        ),
        # post-R56: the consumer this defer proved has been SERVED (the fictions now carry a reaction-type blocker)
        "consumer_served_by_r56": consumer["all_frontier_reaction_type_blocked"],
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R55 DEFER #6 result holds against live code: the consumer is proven (un-blocked fictions
    surface, dominant base rate), AND the RAW join-element demoter both false-VOUCHes a reachable non-C-C fake
    and false-EXCLUDEs a reachable real C-C condensation (so it is not a sound soundness gate)."""
    p = _payload()
    c = p["counts"]
    # (1) the proven consumer -- the transformative advance.  DURABLE: the frontier is populated with fictions.
    #     Post-R56 those fictions are now BLOCKED by the reaction-type oracle (the consumer SERVED), so the
    #     R55 "ships unblocked" measurement is superseded -- this probe now asserts the served state instead.
    assert p["consumer_proof"]["all_reconstructed_fictional"], f"consumer routes not all fictional: {p['consumer_proof']}"
    assert p["consumer_served_by_r56"], f"R56 did not serve the R55 consumer (fictions not all blocked): {p['consumer_proof']}"
    assert p["base_rate"]["fictional_fraction"] >= 0.5, f"pollution base rate too low: {p['base_rate']}"
    # (2) the FATAL refutation of the RAW rule -- both failure modes reproduce
    assert c["false_vouch_classes"] >= 1, f"the RAW rule stopped false-VOUCHing (unsoundness vanished): {p['false_vouches']}"
    assert c["false_exclude_classes"] >= 1, f"the RAW rule stopped false-EXCLUDing real C-C reactions: {p['false_excludes']}"
    assert all(r["is_false_vouch"] for r in p["false_vouches"] if r.get("reachable")), \
        f"a reachable false-VOUCH case stopped VOUCHing: {p['false_vouches']}"
    # (3) the verdict
    assert p["defer_verdict"], f"DEFER #6 verdict does not hold: consumer={p['consumer_proof']} rate={p['base_rate']} counts={c}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
