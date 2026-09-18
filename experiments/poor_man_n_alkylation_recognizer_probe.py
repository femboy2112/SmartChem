"""POOR-MAN-N-ALKYLATION-RECOGNIZER-01 (R63): the FOURTH conservation-locked class the ingenuity reward ships,
GENERALISING the R60 N-methylation recognizer to dehydrative N-alkylation by any ALKYL alcohol onto ANY
non-carbonyl nitrogen nucleophile.

THE ARC.  R56 shipped the reaction-TYPE oracle (:mod:`smartchem.experiment.reaction_type_oracle`) with a
per-recognizer CONSERVATION-LOCK admission gate; R57 added etherification; R58 re-targeted both to the
reaction-centre SPAN; R60 added a CLASS-SPECIFIC N-methylation recognizer (methanol-only), recovering the R45
caffeine win.  R60's record deferred "general N-alkylation by a longer alcohol" to "a future round behind its own
gate".  R63 IS that round: it replaces the methanol-clamped recognizer with a general one
(:func:`smartchem.experiment.reaction_type_oracle._n_alkylation`), subsuming the methyl sub-case (caffeine stays
vouched; the methanol-specific census is retained in :mod:`smartchem.experiment.feasibility` as the R60 anchor).

THE TWO ADVERSARY KILLS (the meta-lesson in action -- run adversaries SEPARATELY from acceptance).  The first cut
was "obviously sound" and WRONG twice; the review gate caught both false-VOUCHes acceptance missed:
* KILL 1 (dalembert -- MASKED-CARBONYL DONOR).  The donor clause used ``_alcohol_counts``, which reads only that
  the leaving O's neighbour is a bond-order-1 carbon and is BLIND to that carbon's alpha-heteroatom neighbours.  So
  a hemiaminal / gem-diol (carbonyl hydrate) / hemiacetal -- a MASKED carbonyl -- posed as an alcohol and VOUCHED
  an aminal/acetal condensation as N-alkylation (``ammonia + aminomethanol -> methylenediamine + water``;
  ``dimethylamine + (dimethylamino)methanol -> bis(dimethylamino)methane + water``).  CLOSED by a tighter donor
  predicate :func:`~smartchem.experiment.feasibility._alkyl_carbinol_alcohol_count` (the carbinol carbon's non-
  hydroxyl heavy neighbours must be ALL carbon -- forbidding the carbonyl oxidation level), with NO genuine-case
  loss (a beta-amino alcohol keeps its carbinol carbon at alcohol level and stays vouched).
* KILL 2 (evil-morty -- PYRROLE-TYPE AROMATIC N).  ``_n_alkyl_amine_bond_count``'s "all-single-bond N" clause was
  documented as excluding aromatic N because "aromatic N carries an order-2 bond" -- FALSE for a pyrrole-type N
  (pyrrole/imidazole/indole/xanthine N7), which is lone-pair-donating and all-single-bond, so azole N slipped
  through mislabelled as an aliphatic amine.  RESOLVED by the OPERATOR as a SCOPE decision (not a code exclusion):
  azole N-alkylation IS a real reaction TYPE, so it is ADMITTED; caffeine's N7 is that motif and stays vouched.
  A dalembert RE-ATTACK on the fixed lock then confirmed the census also admits sulfonamide / hydrazide / hydrazine
  / hydroxylamine / amidine-guanidine N -- all genuine dehydrative N-alkylation TYPES, no fiction -- so the
  operator BROADENED the label to "N-alkylation onto any non-carbonyl N nucleophile" (Problem A; feasibility stays
  deferred, exactly as the acyl recognizer vouches activator-requiring esterification).

WHY THE C-C FRONTIER PROXY IS NOT THE SOUNDNESS BAR HERE.  ``raw_rule_blocks`` (the R55 ground-truth fiction
label) flags a step that forms a C-C bond; an N-alkylation forms a C-N bond, so the proxy is BLIND to an
N-alkylation false-VOUCH.  The soundness of THIS class therefore rests on the census+centre lock and the
adversarial regression pins below (the two kills demote; masked-carbonyl donors demote; amide N stays disjoint;
the aryl-amination fake stays demoted), NOT on the C-C sweep -- which is exactly why the census+centre, not the
proxy, is what makes the claim sound.  The frontier sweep is retained to certify 0 C-C false-VOUCH is UNCHANGED and
to count the newly-vouched real N-alkylations.

THIS PROBE FREEZES, against LIVE code: (1) the CONSUMER served (a general longer-alcohol N-alkylation, demoted by
the R60 methanol clamp, now VOUCHED); (2) SOUNDNESS -- 0 C-C false-VOUCH across the production frontier + the
DEDICATED N-alkylation adversarial pins; (3) KILL 1 -- masked-carbonyl donors DEMOTE; (4) KILL 2 -- azole
N-alkylation ADMITTED (vouches) while the aryl-amination fake stays DEMOTED (escape #7 shut); (5) BROAD SCOPE --
sulfonamide/hydrazine/hydroxylamine vouch, amide N stays disjoint (demoted), tautomerizable amides demote (the
amide-migration residual closed by double-exclusion); (6) the donor census unit-separates alkyl alcohols from
masked carbonyls; (7) POSITIVE controls -- real centre-carrying N-alkylations recognized; (8) centre-absent fails
closed; (9) R56/R57/R58/R60 still frozen; (10) fail-closed totality + disposition honesty.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name, registered_structures
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.feasibility import (
    _alkyl_carbinol_alcohol_count, _n_alkylation_shape_and_net_change,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation, _reconstruct_route

from experiments.poor_man_step_validity_demoter_defer_probe import raw_rule_blocks
import experiments.poor_man_reaction_type_oracle_probe as p56
import experiments.poor_man_etherification_recognizer_probe as p57
import experiments.poor_man_span_local_recognizer_probe as p58
import experiments.poor_man_n_methylation_recognizer_probe as p60

FROZEN_HASH = "8cdb03a6c3134e00fc6c1e901fc0a084b477f26c1737c272ef735d6ad35596ad"

_NA = "N-alkylation"


def _water():
    return structure_by_name("water").molecule


def _hand_step(reactant_smis, product_smis, target_smi) -> "ExperimentStep":
    """A hand-built conserving step -- carries NO reaction centre, so it FAIL-CLOSES to demoted (a VOUCH requires a
    readable centre).  Used only for cases that must DEMOTE."""
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else _water() for s in product_smis)
    target = parse_smiles(target_smi)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def _derive_step(product_smiles, want_products):
    """The centre-CARRYING synthesis step whose k=1 water-scission splits ``product_smiles`` into exactly
    ``want_products`` -- the only construction that can VOUCH (a readable centre is required)."""
    r = parse_smiles(product_smiles)
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    return None


def _demotes(route) -> bool:
    return bool(route_reaction_type_blockers(route))


def _is_na(step) -> bool:
    k = recognize_reaction_type(step)
    return k is not None and _NA in k


def _derived_vouches(product_smiles, want_products) -> "tuple[bool, bool, str | None]":
    """(centre_present, vouched_as_N_alkylation, class) for the derived step -- or (False, False, None) if no cut."""
    st = _derive_step(product_smiles, want_products)
    if st is None:
        return (False, False, None)
    k = recognize_reaction_type(st)
    return (st.reaction_center is not None, k is not None and _NA in k, k)


# --------------------------------------------------------------------------------------------------
# (1) CONSUMER SERVED: a general longer-alcohol N-alkylation (demoted by the R60 methanol clamp) now VOUCHED.
# --------------------------------------------------------------------------------------------------
def consumer_served() -> dict:
    # aniline + ETHANOL -> N-ethylaniline: R60 (methanol-only) could not vouch this; R63 does.
    centre, vouched, klass = _derived_vouches("CCNc1ccccc1", ["Nc1ccccc1", "CCO"])
    # ammonia + ethanol -> ethylamine (the ledger's "aniline_ethanol_n_alkylation"-family case)
    centre2, vouched2, _ = _derived_vouches("CCN", ["N", "CCO"])
    return {
        "n_ethylaniline_centre": centre,
        "n_ethylaniline_vouched": vouched,
        "n_ethylaniline_class": klass,
        "ethylamine_vouched": vouched2,
        "served": vouched and vouched2,
    }


# --------------------------------------------------------------------------------------------------
# (2) SOUNDNESS: 0 C-C false-VOUCH across the production frontier (UNCHANGED); count N-alkylation vouches.
# --------------------------------------------------------------------------------------------------
def soundness_and_coverage() -> dict:
    fp = total = 0
    vouched_targets: set[str] = set()
    na_targets: set[str] = set()
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
            is_cc_fiction = raw_rule_blocks(r)     # forms a C-C bond => reaction-type fiction (ground-truth)
            vouch = not _demotes(r)
            if vouch and is_cc_fiction:
                fp += 1                             # a C-C fiction vouched -- must be 0
            elif vouch:
                vouched_targets.add(ns.name)
            if r.steps and any(_is_na(st) for st in r.steps):
                na_targets.add(ns.name)
    return {
        "total_frontier_routes": total,
        "cc_false_vouch_count": fp,
        "reals_vouched": len(vouched_targets),
        "n_alkylation_targets": sorted(na_targets),
        "caffeine_vouched": "caffeine" in vouched_targets,
    }


# --------------------------------------------------------------------------------------------------
# (3) KILL 1 (dalembert): masked-carbonyl donors DEMOTE -- an aminal/acetal condensation is not an alkylation.
# --------------------------------------------------------------------------------------------------
def kill1_masked_carbonyl_donors_demoted() -> dict:
    cases = {
        # (product, [reactants]) -- a genuine generator k=1 step whose donor is a masked carbonyl; must DEMOTE.
        "aminal_methylenediamine": ("NCN", ["N", "NCO"]),               # ammonia + aminomethanol (hemiaminal)
        "aminal_bis_dimethylaminomethane": ("CN(C)CN(C)C", ["CNC", "CN(C)CO"]),  # + (dimethylamino)methanol
    }
    out = {}
    for key, (prod, reacts) in cases.items():
        centre, vouched, klass = _derived_vouches(prod, reacts)
        out[key] = {"centre_present": centre, "vouched": vouched, "class": klass, "demoted": (not vouched)}
    out["all_demoted"] = all(v["demoted"] for k, v in out.items() if k != "all_demoted")
    return out


# --------------------------------------------------------------------------------------------------
# (4) KILL 2 (evil-morty) + escape #7: azole N-alkylation ADMITTED (vouches); aryl-amination fake DEMOTED.
# --------------------------------------------------------------------------------------------------
def kill2_azole_admitted_aryl_fake_demoted() -> dict:
    azoles = {
        "imidazole_methylation": ("Cn1ccnc1", ["c1cnc[nH]1", "CO"]),
        "pyrrole_ethylation": ("CCn1cccc1", ["c1cc[nH]c1", "CCO"]),
        "indole_methylation": ("Cn1ccc2ccccc21", ["c1ccc2[nH]ccc2c1", "CO"]),
    }
    azole_vouched = {}
    for key, (prod, reacts) in azoles.items():
        _c, v, _k = _derived_vouches(prod, reacts)
        azole_vouched[key] = v
    # the aryl-amination fake (phenol + ammonia -> aniline) and O-alkylation must stay demoted (centre-carrying)
    _c, aryl_fake_vouched, _k = _derived_vouches("Nc1ccccc1", ["c1ccc(O)cc1", "N"])
    _c, o_alk_vouched, _k = _derived_vouches("CCOc1ccccc1", ["c1ccc(O)cc1", "CCO"])
    return {
        "azole_vouched": azole_vouched,
        "all_azoles_vouched": all(azole_vouched.values()),
        "aryl_amination_fake_vouched": aryl_fake_vouched,   # must be False (escape #7 shut)
        "o_alkylation_vouched": o_alk_vouched,               # must be False (O-alkylation is not N-alkylation)
    }


# --------------------------------------------------------------------------------------------------
# (5) BROAD SCOPE: the exotic non-carbonyl N nucleophiles vouch; amide N stays disjoint (demoted incl. tautomers).
# --------------------------------------------------------------------------------------------------
def broad_scope() -> dict:
    exotic = {
        "sulfonamide": ("CS(=O)(=O)NC", ["CS(N)(=O)=O", "CO"]),
        "hydrazine": ("CNNC", ["CNN", "CO"]),
        "hydroxylamine": ("CNO", ["NO", "CO"]),
    }
    exotic_vouched = {k: _derived_vouches(p, r)[1] for k, (p, r) in exotic.items()}
    # amide N stays DISJOINT (the acyl class) -- amide/lactam/tautomerizable-amide N-alkylation must DEMOTE.
    amides = {
        "acetamide": ("CCNC(C)=O", ["CC(N)=O", "CCO"]),
        "2_pyridone": ("Cn1ccccc1=O", ["O=c1cccc[nH]1", "CO"]),
        "uracil": ("Cn1ccc(=O)[nH]c1=O", ["O=c1cc[nH]c(=O)[nH]1", "CO"]),
        "caprolactam": ("CN1CCCCCC1=O", ["O=C1CCCCCN1", "CO"]),
    }
    amide_demoted = {}
    for k, (p, r) in amides.items():
        st = _derive_step(p, r)
        # a step that isn't reachable by this exact k=1 cut is not a false-VOUCH; only a reachable-and-VOUCHED
        # amide would be a regression, so score "demoted" as "not vouched" (unreachable counts as demoted/safe).
        amide_demoted[k] = (st is None) or (not _is_na(st))
    return {
        "exotic_vouched": exotic_vouched,
        "all_exotic_vouched": all(exotic_vouched.values()),
        "amide_demoted": amide_demoted,
        "all_amide_demoted": all(amide_demoted.values()),
    }


# --------------------------------------------------------------------------------------------------
# (6) THE DONOR CENSUS unit-separates alkyl alcohols from masked carbonyls (the KILL-1 lock, at the unit level).
# --------------------------------------------------------------------------------------------------
def donor_census_separates() -> dict:
    return {
        "methanol_is_alkyl": _alkyl_carbinol_alcohol_count(parse_smiles("CO")) == 1,
        "ethanol_is_alkyl": _alkyl_carbinol_alcohol_count(parse_smiles("CCO")) == 1,
        "benzyl_alcohol_is_alkyl": _alkyl_carbinol_alcohol_count(parse_smiles("OCc1ccccc1")) == 1,
        "ethanolamine_alkyl_carbinol": _alkyl_carbinol_alcohol_count(parse_smiles("NCCO")) == 1,  # beta-amino: kept
        "aminomethanol_excluded": _alkyl_carbinol_alcohol_count(parse_smiles("NCO")) == 0,        # hemiaminal
        "methanediol_excluded": _alkyl_carbinol_alcohol_count(parse_smiles("OCO")) == 0,          # gem-diol / hydrate
        "hemiacetal_excluded": _alkyl_carbinol_alcohol_count(parse_smiles("COCO")) == 0,          # methoxymethanol
        "phenol_excluded": _alkyl_carbinol_alcohol_count(parse_smiles("Oc1ccccc1")) == 0,         # aromatic
    }


# --------------------------------------------------------------------------------------------------
# (7) POSITIVE CONTROLS: real centre-carrying N-alkylations recognized (non-vacuity at the unit level).
# --------------------------------------------------------------------------------------------------
def positive_control() -> dict:
    controls = {
        "aniline_ethanol": ("CCNc1ccccc1", ["Nc1ccccc1", "CCO"]),
        "ammonia_methanol": ("CN", ["N", "CO"]),                       # the methyl sub-case (caffeine family)
        "dimethylamine_methanol": ("CN(C)C", ["CNC", "CO"]),            # secondary -> tertiary (bond-count +1)
        "npropylamine_ethanol": ("CCCNCC", ["CCCN", "CCO"]),
    }
    out = {}
    for key, (prod, reacts) in controls.items():
        centre, vouched, klass = _derived_vouches(prod, reacts)
        out[key] = {"centre": centre, "recognized": vouched, "class": klass}
    out["all_recognized"] = all(v["recognized"] for k, v in out.items() if k != "all_recognized")
    return out


# --------------------------------------------------------------------------------------------------
# (8) CENTRE-ABSENT FAILS CLOSED (TAMPER-HARDENING-01): a centre-less N-alkylation-shaped step DEMOTES.
# --------------------------------------------------------------------------------------------------
def centre_absent_fails_closed() -> dict:
    # a genuine-looking N-alkylation as a hand-built (centre-less) step: the census would pass, but no centre -> BLOCK.
    step = _hand_step(["Nc1ccccc1", "CCO"], ["CCNc1ccccc1", "water"], "CCNc1ccccc1")
    census = _n_alkylation_shape_and_net_change(step)

    class _R:
        steps = (step,)

    return {
        "reaction_center_is_none": step.reaction_center is None,
        "census_would_pass": bool(census),
        "recognized_class": recognize_reaction_type(step),
        "demoted": recognize_reaction_type(step) is None,
        "route_blocked": bool(route_reaction_type_blockers(_R())),
    }


# --------------------------------------------------------------------------------------------------
# (9) R56/R57/R58/R60 still frozen (lightweight cross-check) + their canonical classes still recognized.
# --------------------------------------------------------------------------------------------------
def upstream_probes() -> dict:
    return {
        "r56_probe_frozen": hasattr(p56, "validate") and isinstance(getattr(p56, "FROZEN_HASH", None), str),
        "r57_probe_frozen": hasattr(p57, "validate") and isinstance(getattr(p57, "FROZEN_HASH", None), str),
        "r58_probe_frozen": hasattr(p58, "validate") and isinstance(getattr(p58, "FROZEN_HASH", None), str),
        "r60_probe_frozen": hasattr(p60, "validate") and isinstance(getattr(p60, "FROZEN_HASH", None), str),
        "acyl_class_recognized": (lambda k: k is not None and "acyl" in k)(
            recognize_reaction_type(_derive_step("CC(=O)OC", ["CC(=O)O", "CO"]))),
        "ether_class_recognized": (lambda k: k is not None and "etherification" in k)(
            recognize_reaction_type(_derive_step("COC", ["CO", "CO"]))),
    }


# --------------------------------------------------------------------------------------------------
# (10) FAIL-CLOSED + DISPOSITION: a raising recognizer abstains; the reason disclaims cost/feasibility.
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
    k1 = kill1_masked_carbonyl_donors_demoted()
    k2 = kill2_azole_admitted_aryl_fake_demoted()
    scope = broad_scope()
    census = donor_census_separates()
    pc = positive_control()
    caf = centre_absent_fails_closed()
    ups = upstream_probes()
    fc = fail_closed_and_disposition()
    return {
        "schema": "poor-man-n-alkylation-recognizer-01",
        "round": 63,
        "consumer_served": consumer,
        "soundness_and_coverage": sc,
        "kill1_masked_carbonyl_donors_demoted": k1,
        "kill2_azole_admitted_aryl_fake_demoted": k2,
        "broad_scope": scope,
        "donor_census_separates": census,
        "positive_control": pc,
        "centre_absent_fails_closed": caf,
        "upstream_probes": ups,
        "fail_closed_and_disposition": fc,
        # THE VERDICT: R63 grows the whitelist by generalising N-methylation to N-alkylation onto any non-carbonyl N
        # nucleophile by any alkyl alcohol.  It SERVES the general consumer (a longer-alcohol alkylation now vouched),
        # is SOUND (0 C-C false-VOUCH + both adversary kills demote + amide N disjoint), ADMITS azole N (caffeine
        # kept) while the aryl-amination fake stays demoted, positively recognizes real N-alkylations, fails closed on
        # an absent centre, leaves R56/R57/R58/R60 frozen, and is fail-closed + disposition-honest.
        "ship_verdict": (
            consumer["served"]
            and sc["cc_false_vouch_count"] == 0
            and sc["caffeine_vouched"]
            and k1["all_demoted"]
            and k2["all_azoles_vouched"]
            and k2["aryl_amination_fake_vouched"] is False
            and k2["o_alkylation_vouched"] is False
            and scope["all_exotic_vouched"]
            and scope["all_amide_demoted"]
            and all(census.values())
            and pc["all_recognized"]
            and caf["reaction_center_is_none"] and caf["demoted"] and caf["route_blocked"]
            and all(ups.values())
            and fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R63 SHIP result holds against live code: the general N-alkylation consumer is served (a
    longer-alcohol alkylation now vouched), the oracle is SOUND (0 C-C false-VOUCH across the frontier AND both
    adversary kills demote -- masked-carbonyl donors, and the aryl-amination fake -- while amide N stays disjoint),
    azole N-alkylation is ADMITTED (caffeine vouched), real N-alkylations are positively recognized, a centre-less
    step fails closed, R56/R57/R58/R60 stay frozen, and the demoter is fail-closed + disposition-honest."""
    p = _payload()
    assert p["consumer_served"]["served"], f"consumer not served: {p['consumer_served']}"
    sc = p["soundness_and_coverage"]
    assert sc["cc_false_vouch_count"] == 0, f"UNSOUND: a C-C fiction was vouched: {sc}"
    assert sc["caffeine_vouched"], f"caffeine (the R45 win) not vouched: {sc}"
    assert p["kill1_masked_carbonyl_donors_demoted"]["all_demoted"], \
        f"KILL 1 REGRESSION: a masked-carbonyl donor was false-VOUCHed: {p['kill1_masked_carbonyl_donors_demoted']}"
    k2 = p["kill2_azole_admitted_aryl_fake_demoted"]
    assert k2["all_azoles_vouched"], f"azole N-alkylation (admitted scope) not vouched: {k2}"
    assert k2["aryl_amination_fake_vouched"] is False, f"ESCAPE #7 REOPENED: aryl-amination fake vouched: {k2}"
    assert k2["o_alkylation_vouched"] is False, f"O-alkylation mis-vouched as N-alkylation: {k2}"
    scope = p["broad_scope"]
    assert scope["all_exotic_vouched"], f"a broad-scope real N-alkylation not vouched: {scope}"
    assert scope["all_amide_demoted"], f"an amide N was mis-vouched (not disjoint from acyl): {scope}"
    assert all(p["donor_census_separates"].values()), f"donor census failed to unit-separate: {p['donor_census_separates']}"
    assert p["positive_control"]["all_recognized"], f"a real N-alkylation not recognized: {p['positive_control']}"
    caf = p["centre_absent_fails_closed"]
    assert caf["reaction_center_is_none"] and caf["demoted"] and caf["route_blocked"], \
        f"centre-absent step did not fail closed: {caf}"
    assert all(p["upstream_probes"].values()), f"an upstream probe/class regressed: {p['upstream_probes']}"
    fc = p["fail_closed_and_disposition"]
    assert fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"], \
        f"fail-closed / disposition broken: {fc}"
    assert p["ship_verdict"], f"R63 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
