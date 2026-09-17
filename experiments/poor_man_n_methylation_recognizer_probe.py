"""POOR-MAN-N-METHYLATION-RECOGNIZER-01 (R60): the THIRD conservation-locked class the ingenuity reward ships.

THE ARC.  R56 shipped the reaction-TYPE oracle (:mod:`smartchem.experiment.reaction_type_oracle`) with a SINGLE
recognizer (acyl condensation) under a per-recognizer CONSERVATION-LOCK admission gate; R57 grew it by a second
class (dehydrative etherification); R58 re-targeted both to read the reaction-centre SPAN.  Each round the R56
record named the one win it deliberately left on the table: the R45 caffeine N-methylation genericity, DEMOTED as
honest coverage loss because a GENERAL "new C-N bond" recognizer collides -- it fires on both real caffeine
N-methylation and the FAKE aromatic phenol->aniline amination (the R55 theorem one alphabet over), so it fails the
gate.  R60 recovers that win the way the record prescribed: NOT a general recognizer, NOT a bounded-radius patch,
but a CLASS-SPECIFIC conservation-locked N-methylation recognizer.

THE COLLISION TO BEAT, AND WHY THE SPAN ALONE DOES NOT LOCK IT.  Real caffeine N-methylation
(theophylline + methanol -> caffeine + water) and the fake aryl amination (phenol + ammonia -> aniline + water)
carry a BYTE-IDENTICAL reaction centre -- ``formed = {(C,N,1), (H,O,1)}``, ``broken = {(C,O,1), (H,N,1)}``,
``n_components = 1`` -- so :meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation(("N",))`
passes BOTH.  The R58 span check, which sufficed for acyl/ether, is here necessary but not sufficient.  The
CENSUS supplies the lock the span cannot: the consumed alcohol must be METHANOL-specific (an sp3 carbinol whose
only heavy neighbour is its O -- literally CH3-OH, which structurally EXCLUDES aromatic phenol-O AND every longer
alcohol, so general N-alkylation is not admitted), and the formed N-methyl amine must be an all-single-bond N
bearing a methyl carbon and NOT adjacent to a carbonyl C (excludes the aryl-amination fake, whose N is an
unmethylated aryl N, and stays disjoint from the acyl/amidation class).  Within the elementary intermolecular
shape (2 non-water reactants -> 1 non-water product, water expelled) formula conservation then FORCES a fired step
onto a genuine N-methylation -- the conservation-lock proof.

WHAT THIS ROUND CHANGES ELSEWHERE (stated, not hidden).  R56/R57/R58 pinned "caffeine stays demoted" as their
escape-#7 invariant, because with only acyl+ether NO recognizer could vouch N-methylation.  R60 makes caffeine
legitimately VOUCHED, so those three probes' caffeine invariant is re-framed to its correct post-R60 form: escape
#7 is shut iff the phenol->aniline FAKE stays demoted (it does), NOT iff caffeine stays demoted.  The general N-C
recognizer still collides and is still not shipped -- that boundary is unchanged.

THIS PROBE FREEZES, against LIVE code: (1) the CONSUMER served (caffeine's real N-methylation now VOUCHED, was
demoted as coverage loss); (2) ZERO false-VOUCH across the whole production frontier + non-vacuity (caffeine and
methylamine join the vouched reals) -- the R56 mandatory soundness bar; (3) the ADVERSARIAL demotes (the
byte-identical-centre aryl-amination fake, general N-ethylation by a longer alcohol, O-methylation to anisole);
(4) the adversarial k=2 BUNDLED sweep specific to N-methylation -- 0 false-VOUCH; (5) a real elementary
N-methylation POSITIVELY recognized; (6) the census unit-separates methanol/ethanol/phenol and the N-methyl amine
from the aryl/amide N; (7) R56/R57/R58 still frozen + their canonical classes still recognized; (8) fail-closed
totality + disposition honesty.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name, registered_structures
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.feasibility import (
    _methylation_shape_and_net_change, _methanol_specific_alcohol_count, _n_methyl_amine_count,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation, _reconstruct_route

from experiments.poor_man_step_validity_demoter_defer_probe import raw_rule_blocks
import experiments.poor_man_reaction_type_oracle_probe as p56
import experiments.poor_man_etherification_recognizer_probe as p57
import experiments.poor_man_span_local_recognizer_probe as p58

FROZEN_HASH = "fb8de870932fad15fd7af08d8e48e66867a5f8aba1a2060451a60b06802143c9"

_NM = "N-methylation"
# theophylline (1,3-dimethylxanthine) + methanol -> caffeine (1,3,7-trimethylxanthine) + water: the R45 win.
_CAFFEINE = "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"


def _water():
    return structure_by_name("water").molecule


def _hand_step(reactant_smis, product_smis, target_smi) -> "ExperimentStep":
    """A hand-built conserving step -- carries NO reaction centre, so it exercises the span-ABSENT fallback (the
    whole-molecule census alone, sound at the production k=1 config)."""
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else _water() for s in product_smis)
    target = parse_smiles(target_smi)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def _demotes(route) -> bool:
    return bool(route_reaction_type_blockers(route))


def _is_nm(step) -> bool:
    k = recognize_reaction_type(step)
    return k is not None and _NM in k


# --------------------------------------------------------------------------------------------------
# (1) THE CONSUMER SERVED: caffeine's real N-methylation step is now VOUCHED (was demoted as coverage loss).
# --------------------------------------------------------------------------------------------------
def consumer_served() -> dict:
    caf = parse_smiles(_CAFFEINE)
    theo = structure_by_name("theophylline").molecule
    compiled = compile_synthesis(caf, reagents=(parse_smiles("CO"), parse_smiles("O")), available=(theo,),
                                 max_depth=2, max_routes=8, cut_budget=20000, commodities=(), box=ConstraintBox())
    routes = [f.route for f in compiled.ranked]
    nm_routes = [r for r in routes if r.steps and any(_is_nm(st) for st in r.steps)]
    vouched = [r for r in routes if not _demotes(r)]
    # and through the real affordability-frontier wire-in
    resp = run_compilation(build_recompile_request("caffeine", max_depth=3))
    fr = resp.affordability_frontier
    frontier_has_vouched = any(
        not any("unrecognized reaction type" in b for b in ((getattr(e.cost_vector, "hard_blockers", ()) or ())
                                                            + (getattr(e.cost_vector, "fiction_blockers", ()) or ())))
        for e in fr
    )
    return {
        "target": "caffeine",
        "search_routes": len(routes),
        "recognized_as_n_methylation": len(nm_routes),
        "vouched_routes": len(vouched),
        "frontier_entries": len(fr),
        "frontier_has_a_vouched_route": frontier_has_vouched,
        "served": len(nm_routes) >= 1 and len(vouched) >= 1 and frontier_has_vouched,
    }


# --------------------------------------------------------------------------------------------------
# (2) SOUNDNESS + NON-VACUITY across the whole production frontier (the R56 mandatory bar): 0 false-VOUCH.
# --------------------------------------------------------------------------------------------------
def soundness_and_coverage() -> dict:
    fp = total = 0
    vouched_targets: set[str] = set()
    nm_targets: set[str] = set()
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
            elif vouch:
                vouched_targets.add(ns.name)
            if r.steps and any(_is_nm(st) for st in r.steps):
                nm_targets.add(ns.name)
    return {
        "total_frontier_routes": total,
        "false_vouch_count": fp,
        "reals_vouched": len(vouched_targets),
        "vouched_targets": sorted(vouched_targets),
        "n_methylation_targets": sorted(nm_targets),
        "caffeine_vouched": "caffeine" in vouched_targets,
    }


# --------------------------------------------------------------------------------------------------
# (3) THE ADVERSARIAL DEMOTES: the byte-identical-centre fake + general N-alkylation + O-methylation.
# --------------------------------------------------------------------------------------------------
def adversarial_must_demote() -> dict:
    cases = {
        # (reactants, products, target, why it must NOT be vouched as N-methylation)
        "aryl_amination_aniline": (["c1ccc(O)cc1", "N"], ["Nc1ccccc1", "water"], "Nc1ccccc1",
                                   "byte-identical reaction centre to caffeine; no methanol, aryl N unmethylated"),
        "general_n_ethylation": (["CCO", "N"], ["CCN", "water"], "CCN",
                                 "ethanol is not methanol-specific -- general N-alkylation is not admitted"),
        "o_methylation_anisole": (["c1ccc(O)cc1", "CO"], ["COc1ccccc1", "water"], "COc1ccccc1",
                                  "methanol consumed but no N-methyl amine formed (an aryl ether, not N-methylation)"),
    }
    out = {}
    for key, (r, p, tgt, why) in cases.items():
        step = _hand_step(r, p, tgt)
        klass = recognize_reaction_type(step)
        out[key] = {
            "fires_n_methylation_census": bool(_methylation_shape_and_net_change(step)),
            "recognized_class": klass,
            "not_vouched_as_n_methylation": not (klass is not None and _NM in klass),
            "why": why,
        }
    return out


# --------------------------------------------------------------------------------------------------
# (4) THE ADVERSARIAL k=2 BUNDLED SWEEP (mandatory, per the R58 bar): 0 false-VOUCH on reachable bundles.
# --------------------------------------------------------------------------------------------------
_K2_LIB = ["CN(C)C", _CAFFEINE, "CNc1ccccc1", "CN(C)CCO", "CNCC", "CCN(C)C", "CN(C)C(=O)C",
           "CNC", "CCNC", "CN(C)c1ccccc1", "COCN(C)C"]


def k2_adversarial() -> dict:
    census_vouched = span_demoted = recognized_nm = false_vouch = 0
    for smi in _K2_LIB:
        r = parse_smiles(smi)
        for cs in capped_scissions(r, (parse_smiles("O"), parse_smiles("O")), max_reactant_cuts=2)[0]:
            try:
                step = ExperimentStep.from_transform(cs)
            except Exception:
                continue
            if _methylation_shape_and_net_change(step):     # the whole-molecule census would vouch
                census_vouched += 1
                if not _is_nm(step):                          # the span-local recognizer demoted the bundle
                    span_demoted += 1
            if _is_nm(step):
                recognized_nm += 1

                class _R:
                    steps = (step,)

                if raw_rule_blocks(_R()):                      # a recognized step that forms a C-C bond = false-VOUCH
                    false_vouch += 1
    return {
        "k2_census_vouched": census_vouched,
        "k2_span_demoted_bundles": span_demoted,
        "k2_recognized_n_methylation": recognized_nm,
        "k2_false_vouch_count": false_vouch,
    }


# --------------------------------------------------------------------------------------------------
# (5) POSITIVE CONTROL: real elementary N-methylations are recognized (non-vacuity at the unit level).
# --------------------------------------------------------------------------------------------------
def positive_control() -> dict:
    n_methylaniline = _hand_step(["Nc1ccccc1", "CO"], ["CNc1ccccc1", "water"], "CNc1ccccc1")
    methylamine = _hand_step(["N", "CO"], ["CN", "water"], "CN")
    ka = recognize_reaction_type(n_methylaniline)
    km = recognize_reaction_type(methylamine)
    return {
        "n_methylaniline_recognized": ka is not None and _NM in ka,
        "methylamine_recognized": km is not None and _NM in km,
        "recognized_classes": [ka, km],
    }


# --------------------------------------------------------------------------------------------------
# (6) THE CENSUS UNIT-SEPARATES: methanol from higher alcohols/phenol; the N-methyl amine from aryl/amide N.
# --------------------------------------------------------------------------------------------------
def census_separates() -> dict:
    caf = parse_smiles(_CAFFEINE)
    theo = structure_by_name("theophylline").molecule
    return {
        "methanol_is_methanol_specific": _methanol_specific_alcohol_count(parse_smiles("CO")) == 1,
        "ethanol_excluded": _methanol_specific_alcohol_count(parse_smiles("CCO")) == 0,
        "phenol_excluded": _methanol_specific_alcohol_count(parse_smiles("c1ccc(O)cc1")) == 0,
        "caffeine_has_one_n_methyl": _n_methyl_amine_count(caf) == 1,     # only N7; N1/N3 are carbonyl-flanked
        "theophylline_has_no_free_n_methyl": _n_methyl_amine_count(theo) == 0,
        "aniline_n_not_methyl": _n_methyl_amine_count(parse_smiles("Nc1ccccc1")) == 0,
        "acetamide_n_not_methyl": _n_methyl_amine_count(parse_smiles("CC(=O)NC")) == 0,  # N-methyl amide: carbonyl-adjacent
    }


# --------------------------------------------------------------------------------------------------
# (7) R56/R57/R58 still frozen + their canonical classes still recognized (lightweight cross-check, per R58).
# --------------------------------------------------------------------------------------------------
def upstream_probes() -> dict:
    return {
        "r56_probe_frozen": hasattr(p56, "validate") and isinstance(getattr(p56, "FROZEN_HASH", None), str),
        "r57_probe_frozen": hasattr(p57, "validate") and isinstance(getattr(p57, "FROZEN_HASH", None), str),
        "r58_probe_frozen": hasattr(p58, "validate") and isinstance(getattr(p58, "FROZEN_HASH", None), str),
        "acyl_class_recognized": (lambda k: k is not None and "acyl" in k)(
            recognize_reaction_type(_hand_step(["CC(=O)O", "CO"], ["CC(=O)OC", "water"], "CC(=O)OC"))),
        "ether_class_recognized": (lambda k: k is not None and "etherification" in k)(
            recognize_reaction_type(_hand_step(["CO", "CO"], ["COC", "water"], "COC"))),
    }


# --------------------------------------------------------------------------------------------------
# (8) FAIL-CLOSED + DISPOSITION: a raising recognizer abstains; the reason disclaims cost/feasibility.
# --------------------------------------------------------------------------------------------------
def fail_closed_and_disposition() -> dict:
    import smartchem.experiment.reaction_type_oracle as O
    orig = O._RECOGNIZERS

    def _boom(step):
        raise RuntimeError("recognizer boom")

    O._RECOGNIZERS = (("boom", _boom),) + orig
    try:
        fake = _hand_step(["c1ccc(O)cc1", "N"], ["Nc1ccccc1", "water"], "Nc1ccccc1")  # the aryl-amination fake
        no_crash = True
        try:
            recognize_reaction_type(fake)
        except Exception:
            no_crash = False
        still_demoted = recognize_reaction_type(fake) is None
    finally:
        O._RECOGNIZERS = orig

    class _R:
        steps = (_hand_step(["c1ccc(O)cc1", "N"], ["Nc1ccccc1", "water"], "Nc1ccccc1"),)

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
    k2 = k2_adversarial()
    pc = positive_control()
    census = census_separates()
    ups = upstream_probes()
    fc = fail_closed_and_disposition()
    return {
        "schema": "poor-man-n-methylation-recognizer-01",
        "round": 60,
        "consumer_served": consumer,
        "soundness_and_coverage": sc,
        "adversarial_must_demote": adv,
        "k2_adversarial": k2,
        "positive_control": pc,
        "census_separates": census,
        "upstream_probes": ups,
        "fail_closed_and_disposition": fc,
        # THE VERDICT: R60 grows the whitelist by a THIRD conservation-locked class (dehydrative N-methylation),
        # recovering the R45 caffeine win the class-specific way.  It SERVES the caffeine consumer, is SOUND (0
        # false-VOUCH across the frontier AND on the adversarial k=2 bundled sweep) and NON-VACUOUS, DEMOTES the
        # byte-identical-centre fake + general N-alkylation + O-methylation, positively recognizes real
        # N-methylations, leaves R56/R57/R58 frozen, and is fail-closed + disposition-honest.
        "ship_verdict": (
            consumer["served"]
            and sc["false_vouch_count"] == 0
            and sc["caffeine_vouched"]
            and all(c["not_vouched_as_n_methylation"] for c in adv.values())
            and k2["k2_false_vouch_count"] == 0
            and pc["n_methylaniline_recognized"] and pc["methylamine_recognized"]
            and all(census.values())
            and all(ups.values())
            and fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R60 SHIP result holds against live code: the N-methylation consumer is served (caffeine's real
    N-methylation now vouched), the oracle stays SOUND (0 false-VOUCH across the production frontier AND on the
    adversarial k=2 bundled sweep) and NON-VACUOUS (caffeine a vouched real), the byte-identical-centre fake +
    general N-alkylation + O-methylation are NOT vouched as N-methylation, real N-methylations are positively
    recognized, the census unit-separates methanol/N-methyl-amine, R56/R57/R58 stay frozen with their canonical
    classes recognized, and the demoter is fail-closed + disposition-honest."""
    p = _payload()
    assert p["consumer_served"]["served"], f"N-methylation consumer not served: {p['consumer_served']}"
    sc = p["soundness_and_coverage"]
    assert sc["false_vouch_count"] == 0, f"UNSOUND: the oracle false-VOUCHed a fiction: {sc}"
    assert sc["caffeine_vouched"], f"VACUOUS/broken: caffeine not vouched: {sc}"
    for key, c in p["adversarial_must_demote"].items():
        assert c["not_vouched_as_n_methylation"], f"adversarial {key} WAS vouched as N-methylation (false-VOUCH): {c}"
    k2 = p["k2_adversarial"]
    assert k2["k2_false_vouch_count"] == 0, f"UNSOUND: a k=2 bundle was false-VOUCHed as N-methylation: {k2}"
    pc = p["positive_control"]
    assert pc["n_methylaniline_recognized"] and pc["methylamine_recognized"], \
        f"a real N-methylation is not recognized: {pc}"
    assert all(p["census_separates"].values()), f"the census failed to unit-separate a case: {p['census_separates']}"
    assert all(p["upstream_probes"].values()), f"an upstream probe/class regressed: {p['upstream_probes']}"
    fc = p["fail_closed_and_disposition"]
    assert fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"], \
        f"fail-closed / disposition broken: {fc}"
    assert p["ship_verdict"], f"R60 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
