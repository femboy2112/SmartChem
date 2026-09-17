"""POOR-MAN-ETHERIFICATION-RECOGNIZER-01 (R57): the SECOND conservation-locked class the ingenuity reward ships.

THE ARC.  R56 shipped the reaction-TYPE oracle (:mod:`smartchem.experiment.reaction_type_oracle`) with a SINGLE
recognizer -- acyl condensation -- and a per-recognizer CONSERVATION-LOCK admission gate: a recognizer is admitted
only if, within a tight elementary shape, formula conservation FORCES a fired step onto a genuine instance of the
class (so a formula-conserving fake cannot share its feature).  R57 GROWS the whitelist by one class -- dehydrative
etherification (2 R-OH -> R-O-R + water) -- under that same gate.  It is NOT a bounded-radius patch (escape #7): it
is a positively-attested class whose unbounded-ness surfaces as coverage loss, never a false-VOUCH.

THE STEER (the user's R57 question).  "Are we hard-coding chemistry, or the RULES of chemistry so chemistry drops
out? Let the category theory do the heavy lifting."  The design gate's answer, verified against the tree: the tree
has NO span/DPO rule-algebra to derive recognizers from (transform_registry is a provenance digest; the grammar is
imperative), so the literal "recognizer set drops out of category theory" is a cathedral this round.  BUT the
generator DOES already compute the categorical rewrite of each step -- ``CappedScission.cut``/``.caps`` (a
valence-certified span) -- and then DISCARDS it at ``ExperimentStep.from_transform``.  Reading that span is the
genuine structural fix (R58); it is a step-schema + serialization change (the step digest is derived from all
fields; the replay payload has fixed fields), so it is scoped as its own round.  R57 ships the etherification
recognizer at the step level -- sound at the production config (k=1) -- at the SAME bar the shipped acyl recognizer
already meets, with the shared k=1 locality documented honestly.

THE CONSERVATION-LOCK (three clauses, each earning its place against a reachable/near-miss fake):
* net dialkyl (sp3 C-O-C) ether-O FORMED -- the aryl-ether fake (phenol + methanol -> anisole + water) forms an
  ether-O with an AROMATIC neighbour, which is not a dialkyl ether, so it is DEMOTED;
* net sp3 alcohol CONSUMED -- the peroxide-coupling fake (EtOOH + ethane -> Et2O + water) consumes NO alcohol (a
  hydroperoxide O-O-H is not an alcohol), so it is DEMOTED;
* NO ether-O among the reactants -- the bundled non-local fiction (ethylene glycol + dimethyl ether ->
  dimethoxyethane + water) REUSES a reactant ether, so it is DEMOTED even at k >= 2 (dalembert's demonstrated kill).

THIS PROBE FREEZES, against LIVE code: (1) the CONSUMER served (dimethyl ether -- 2 methanol -> DME + water -- now
VOUCHED as etherification, was demoted); (2) ZERO false-VOUCH across the whole production frontier + non-vacuity
(dimethyl ether joins the genuine reals); (3) the three ADVERSARIAL fakes (peroxide / anisole / glycol+DME) all
DEMOTED; (4) a real elementary etherification is POSITIVELY recognized; (5) the acyl recognizer + isopentyl-acetate
C-C fictions UNREGRESSED (R56 still validates); (6) the aromatic-amination FAKE stays demoted (escape #7 shut; R60
re-framing -- caffeine is now vouched by the class-specific N-methylation recognizer, not by this one); (7) FAIL-CLOSED
totality + disposition honesty.

TAMPER-HARDENING-01 UPDATE (hash re-frozen ae5de300 -> 6d783d59).  The centre-less census fallback the etherification
recognizer carried is RETIRED (a nulled ``reaction_center`` in a serialized replay must fail-closed, not census-vouch
-- the fiction tamper channel).  So (4)'s positive control is rebuilt from a hand-built centre-LESS step to a
centre-CARRYING derived one (a centre-less step now demotes), and gains a ``dme_step_carries_centre`` assertion.  The
recognized class + soundness are IDENTICAL (0 false-VOUCH, dimethyl ether still a vouched real over the centre-carrying
frontier sweep); only the positive-control's shape moved, so the frozen hash is re-frozen to the post-hardening truth.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name, registered_structures
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.feasibility import (
    _is_intermolecular_etherification, _ether_oxygen_counts, _alcohol_counts,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation, _reconstruct_route

# reuse the R55/R56 probe helpers (the C-C rule is the ground-truth fiction LABEL for the soundness cross-tab)
from experiments.poor_man_step_validity_demoter_defer_probe import _resolve, _routes_of, raw_rule_blocks
import experiments.poor_man_reaction_type_oracle_probe as p56

FROZEN_HASH = "6d783d59b1f50a36eb106a10b510e545f9e3895ef55fafcf1f95fad59fdcffda"

_ETHER_CLASS = "etherification"


def _routes(tsmi, avail, reags=None):
    tgt = parse_smiles(tsmi)
    av = tuple(_resolve(t) for t in avail)
    kw = {"available": av, "commodities": ()}
    if reags is not None:
        kw["reagents"] = tuple(_resolve(t) for t in reags)
    return _routes_of(compile_synthesis(tgt, **kw))


def _water():
    return structure_by_name("water").molecule


def _hand_step(reactant_smis, product_smis, target_smi):
    """A hand-constructed conserving step (the deterministic adversarial harness, mirroring the R52 defer probe):
    lets us pin the recognizer on fakes whose compile-reachability is config-dependent, without a live search."""
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else _water() for s in product_smis)
    target = parse_smiles(target_smi)
    # locate the target instance among the products (identity by formula+charge is enough here)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def _derive_step(product_smiles, want_products):
    """The centre-CARRYING synthesis step whose k=1 decomposition splits ``product_smiles`` (+ water) into exactly
    ``want_products`` -- a real :class:`ReactionCenter` built ``from_transform`` on a CappedScission.  TAMPER-HARDENING-01
    retired the centre-less census fallback, so a POSITIVE etherification control must now carry a readable centre (a
    hand-built centre-less step fail-closes to demoted); an adversarial fake, which must demote regardless, may stay
    centre-less."""
    r = parse_smiles(product_smiles)
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    return None


def _demotes(route) -> bool:
    return bool(route_reaction_type_blockers(route))


# --------------------------------------------------------------------------------------------------
# (1) THE CONSUMER SERVED: dimethyl ether (2 methanol -> DME + water) is now VOUCHED as etherification.
# --------------------------------------------------------------------------------------------------
def consumer_served() -> dict:
    # live search route
    routes = _routes("COC", ["methanol"], reags=["water"])
    ether_routes = [
        r for r in routes
        if r.steps and all(recognize_reaction_type(st) is not None
                           and _ETHER_CLASS in recognize_reaction_type(st) for st in r.steps)
    ]
    vouched = [r for r in routes if not _demotes(r)]
    # and through the real affordability-frontier wire-in
    resp = run_compilation(build_recompile_request("dimethyl ether", max_depth=3))
    fr = resp.affordability_frontier
    frontier_has_vouched = any(
        not any("unrecognized reaction type" in b for b in ((getattr(e.cost_vector, "hard_blockers", ()) or ()) + (getattr(e.cost_vector, "fiction_blockers", ()) or ())))
        for e in fr
    )
    return {
        "target": "dimethyl ether",
        "search_routes": len(routes),
        "recognized_as_etherification": len(ether_routes),
        "vouched_routes": len(vouched),
        "frontier_entries": len(fr),
        "frontier_has_a_vouched_route": frontier_has_vouched,
        "served": len(ether_routes) >= 1 and len(vouched) >= 1 and frontier_has_vouched,
    }


# --------------------------------------------------------------------------------------------------
# (2) SOUNDNESS + NON-VACUITY across the whole production frontier: 0 false-VOUCH, dimethyl ether now a real.
# --------------------------------------------------------------------------------------------------
def soundness_and_coverage() -> dict:
    fp = total = 0
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
            is_fiction = raw_rule_blocks(r)          # C-C bond => reaction-type fiction (ground-truth label)
            vouch = not _demotes(r)
            if vouch and is_fiction:
                fp += 1                               # FALSE-VOUCH -- the catastrophic error; must be 0
            elif vouch and not is_fiction:
                vouched_targets.add(ns.name)
    return {
        "total_frontier_routes": total,
        "false_vouch_count": fp,
        "reals_vouched": len(vouched_targets),
        "vouched_targets": sorted(vouched_targets),
        "dimethyl_ether_vouched": "dimethyl ether" in vouched_targets,
    }


# --------------------------------------------------------------------------------------------------
# (3) THE THREE ADVERSARIAL FAKES: each demoted, each by a DIFFERENT clause of the conservation-lock.
# --------------------------------------------------------------------------------------------------
def adversarial_must_demote() -> dict:
    cases = {
        # (reactants, products, target, why it must be demoted)
        "peroxide_coupling": (["CCOO", "CC"], ["CCOCC", "water"], "CCOCC", "no alcohol consumed"),
        "aryl_ether_anisole": (["c1ccc(O)cc1", "CO"], ["COc1ccccc1", "water"], "COc1ccccc1", "aryl ether, not dialkyl"),
        "bundled_glycol_dme": (["OCCO", "COC"], ["COCCOC", "water"], "COCCOC", "reuses a reactant ether"),
    }
    out = {}
    for key, (r, p, tgt, why) in cases.items():
        step = _hand_step(r, p, tgt)
        out[key] = {
            "fires_etherification": bool(_is_intermolecular_etherification(step)),
            "recognized_class": recognize_reaction_type(step),
            "demoted": recognize_reaction_type(step) is None,
            "why": why,
        }
    return out


# --------------------------------------------------------------------------------------------------
# (4) POSITIVE CONTROL: a real elementary etherification is recognized (non-vacuity at the unit level).
# --------------------------------------------------------------------------------------------------
def positive_control() -> dict:
    step = _derive_step("COC", ["CO", "CO"])   # 2 methanol -> DME + water, centre-CARRYING (TAMPER-HARDENING-01)
    klass = recognize_reaction_type(step) if step is not None else None
    return {
        "dme_step_carries_centre": step is not None and step.reaction_center is not None,
        "dme_step_recognized": klass is not None and _ETHER_CLASS in klass,
        "recognized_class": klass,
        "ether_o_formed": _ether_oxygen_counts(parse_smiles("COC")) - 2 * _ether_oxygen_counts(parse_smiles("CO")),
        "alcohol_consumed": 2 * _alcohol_counts(parse_smiles("CO")) - _alcohol_counts(parse_smiles("COC")),
    }


# --------------------------------------------------------------------------------------------------
# (5) UNREGRESSED: R56 acyl still validates; the isopentyl-acetate C-C fictions still demoted.
# --------------------------------------------------------------------------------------------------
def acyl_unregressed() -> dict:
    r56_ok = p56.validate()
    r56_hash = p56.content_hash() == p56.FROZEN_HASH
    fictions = _routes("CC(=O)OCCC(C)C", ["CC(C)O", "CCOC(C)=O"])
    return {
        "r56_probe_validates": r56_ok,
        "r56_hash_stable": r56_hash,
        "isopentyl_fictions_reachable": bool(fictions),
        "isopentyl_fictions_all_demoted": bool(fictions) and all(_demotes(r) for r in fictions),
    }


# --------------------------------------------------------------------------------------------------
# (6) ESCAPE #7 STAYS SHUT (R60 re-framing): the ETHERIFICATION recognizer cannot vouch N-methylation -- caffeine
#     is now vouched by R60's CLASS-SPECIFIC recognizer, not by this class, and the aromatic-amination FAKE stays
#     demoted (the real escape-#7 invariant, unchanged by R57).
# --------------------------------------------------------------------------------------------------
def caffeine_now_vouched_fake_demoted() -> dict:
    routes = _routes_of(compile_synthesis(structure_by_name("caffeine").molecule, max_depth=2))
    fake = _routes("Nc1ccc(N)cc1", ["ammonia", "4-aminophenol"])   # the R55 aromatic-amination fake
    return {
        "caffeine_reachable": bool(routes),
        "caffeine_has_vouched_route": bool(routes) and any(not _demotes(r) for r in routes),
        "amination_fake_reachable": bool(fake),
        "amination_fake_demoted": bool(fake) and all(_demotes(r) for r in fake),
    }


# --------------------------------------------------------------------------------------------------
# (7) FAIL-CLOSED + DISPOSITION HONESTY: a raising recognizer abstains; the demotion reason disclaims feasibility.
# --------------------------------------------------------------------------------------------------
def fail_closed_and_disposition() -> dict:
    import smartchem.experiment.reaction_type_oracle as O
    orig = O._RECOGNIZERS

    def _boom(step):
        raise RuntimeError("recognizer boom")

    O._RECOGNIZERS = (("boom", _boom),) + orig
    try:
        fake = _hand_step(["CCOO", "CC"], ["CCOCC", "water"], "CCOCC")  # peroxide fake
        no_crash = True
        try:
            recognize_reaction_type(fake)
        except Exception:
            no_crash = False
        still_demoted = recognize_reaction_type(fake) is None
    finally:
        O._RECOGNIZERS = orig
    # disposition honesty: the reason string names the type, disclaims cost/feasibility
    fake2 = _hand_step(["CCOO", "CC"], ["CCOCC", "water"], "CCOCC")

    class _R:
        steps = (fake2,)
    reasons = route_reaction_type_blockers(_R())
    honest = bool(reasons) and all(
        "unrecognized reaction type" in b and "NOT a claim of cost or feasibility" in b for b in reasons
    )
    return {
        "no_crash_on_raising_recognizer": no_crash,
        "fake_still_demoted": still_demoted,
        "disposition_honest": honest,
    }


def _payload() -> dict:
    consumer = consumer_served()
    sc = soundness_and_coverage()
    adv = adversarial_must_demote()
    pc = positive_control()
    unreg = acyl_unregressed()
    caff = caffeine_now_vouched_fake_demoted()
    fc = fail_closed_and_disposition()
    return {
        "schema": "poor-man-etherification-recognizer-01",
        "round": 57,
        "consumer_served": consumer,
        "soundness_and_coverage": sc,
        "adversarial_must_demote": adv,
        "positive_control": pc,
        "acyl_unregressed": unreg,
        "caffeine_now_vouched_fake_demoted": caff,
        "fail_closed_and_disposition": fc,
        # THE VERDICT: R57 grows the whitelist by a SECOND conservation-locked class (dehydrative etherification).
        # It SERVES a live consumer (dimethyl ether), is SOUND (0 false-VOUCH across the frontier) and NON-VACUOUS,
        # DEMOTES all three adversarial fakes (each by a distinct clause), leaves acyl + the C-C fictions
        # UNREGRESSED, keeps escape #7 shut (the aromatic-amination FAKE stays demoted; caffeine is now vouched by
        # R60's class-specific recognizer, not this one), and is fail-closed + disposition-honest.
        "ship_verdict": (
            consumer["served"]
            and sc["false_vouch_count"] == 0
            and sc["dimethyl_ether_vouched"]
            and all(c["demoted"] for c in adv.values())
            and pc["dme_step_carries_centre"] and pc["dme_step_recognized"]
            and unreg["r56_probe_validates"] and unreg["isopentyl_fictions_all_demoted"]
            and caff["amination_fake_demoted"]
            and fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R57 SHIP result holds against live code: the etherification consumer is served (dimethyl ether
    vouched), the oracle stays SOUND (0 false-VOUCH across the production frontier) and NON-VACUOUS (dimethyl ether
    a real), all three adversarial fakes are demoted (each by a distinct conservation-lock clause), a real
    etherification is positively recognized, the acyl recognizer + C-C fictions are unregressed, escape #7 stays
    shut (the aromatic-amination fake demoted; caffeine is now vouched by R60's class-specific recognizer, not this
    one), and the demoter is fail-closed + disposition-honest."""
    p = _payload()
    assert p["consumer_served"]["served"], f"etherification consumer not served: {p['consumer_served']}"
    sc = p["soundness_and_coverage"]
    assert sc["false_vouch_count"] == 0, f"UNSOUND: the oracle false-VOUCHed a fiction: {sc}"
    assert sc["dimethyl_ether_vouched"], f"VACUOUS/broken: dimethyl ether not vouched: {sc}"
    for key, c in p["adversarial_must_demote"].items():
        assert c["demoted"], f"adversarial fake {key} NOT demoted (false-VOUCH risk): {c}"
    assert p["positive_control"]["dme_step_carries_centre"], \
        f"the etherification positive control lost its reaction centre (TAMPER-HARDENING-01 needs one): {p['positive_control']}"
    assert p["positive_control"]["dme_step_recognized"], f"a real etherification is not recognized: {p['positive_control']}"
    assert p["acyl_unregressed"]["r56_probe_validates"], "R56 acyl probe no longer validates -- regression"
    assert p["acyl_unregressed"]["isopentyl_fictions_all_demoted"], "an isopentyl C-C fiction stopped being demoted"
    assert p["caffeine_now_vouched_fake_demoted"]["amination_fake_demoted"], \
        "escape #7 REOPENED: the aromatic-amination fake was vouched"
    fc = p["fail_closed_and_disposition"]
    assert fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"], \
        f"fail-closed / disposition broken: {fc}"
    assert p["ship_verdict"], f"R57 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
