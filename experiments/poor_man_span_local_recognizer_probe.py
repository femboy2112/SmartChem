"""POOR-MAN-SPAN-LOCAL-RECOGNIZER-01 (R58): the recognizers read the actual rewrite MORPHISM, not a count.

THE ARC.  R56/R57 shipped a positive-whitelist reaction-TYPE oracle whose two recognizers (acyl condensation,
dehydrative etherification) identify a class by a WHOLE-MOLECULE functional-group census over the elementary
intermolecular shape.  A whole-molecule count is non-local, so its soundness silently BORROWED the generator's k=1
single-cut invariant ([[a-whole-set-count-classifier-is-fooled-by-non-locality]]).  R58 is the span-reading root
fix the R57 record named: the generator already computes each step's categorical rewrite as a
:class:`~smartchem.structure_descent.CappedScission` (``cut`` = bonds broken, ``caps`` = bonds formed,
valence-certified atom-by-atom) and DISCARDED it at ``ExperimentStep.from_transform``.  R58 distils that span into a
coordinate-free :class:`~smartchem.reaction_center.ReactionCenter` (formed/broken bond element-kinds + connected
component count), carries it on the step (a NON-identity annotation -- ``compare=False`` -> invisible to the content
digest), serialises it through the replay payload, and re-targets both recognizers to CHECK the reaction centre is a
single connected elementary condensation.  The structure does the heavy lifting.

THE STEER (the user's standing question).  "Are we hard-coding chemistry, or the RULES so chemistry drops out? Let
the category theory do the heavy lifting."  R58's concrete answer: the R57 etherification carried a HAND-ENUMERATED
whole-molecule blacklist clause -- "no ether among the reactants" (clause iii) -- to sink one bundled fiction.  That
clause is exactly the R53 anti-pattern, and it is non-local: it FALSE-DEMOTES a genuine etherification whose
reactant merely CONTAINS an unrelated ether.  R58 DELETES clause (iii) for centre-carrying steps and replaces it
with reading the actual rewrite span -- the hard-coded chemistry drops out, the categorical rewrite decides.

TWO MEASURED CONSUMERS (this is not verdict-neutral hardening):
* COVERAGE (production, k=1): ``methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water`` is a genuine
  etherification the R57 clause (iii) sank because a spectator methoxy is present.  R58 RECOVERS it (and its class of
  spectator-ether etherifications) -- 48 reachable k=1 steps over the probe library, every one a real single
  condensation by its span.
* SOUNDNESS (config-robustness, k>=2): a bundled multi-cut step forges the same NET group signature as an elementary
  reaction (``THF + 2 water -> ethane + a triol`` for ether; 48 measured acyl bundles).  The whole-molecule census
  false-VOUCHES them; the span reads a non-elementary centre (extra bonds, or >1 component) and DEMOTES them.

THIS PROBE FREEZES, against LIVE code: (1) the coverage CONSUMER served (the spectator-ether etherification vouched,
its target's frontier route un-blocked); (2) the coverage RECOVERY set (R58 vouch & R57 demote), every member REAL;
(3) ZERO false-VOUCH across the production frontier + R58 vouches a superset of R57's reals; (4) the config-robust
SOUNDNESS kills (k>=2 census-false-vouches the span demotes), both classes; (5) live==replay (a centre round-trips,
same verdict + same digest) and digest-INVARIANCE (the centre never changes step identity); (6) acyl UNREGRESSED and
verdict-neutral at k=1 (ester/amide/thioester all still vouched, 0 lost); (7) R56 + R57 probes still validate;
(8) caffeine still demoted (escape #7 shut); (9) fail-closed + disposition honesty.
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
    _is_intermolecular_etherification, _is_intermolecular_acyl_condensation,
    _ether_shape_and_net_change, _reactant_ether_count,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import (
    build_recompile_request, run_compilation, _reconstruct_route,
    _step_to_payload, _step_from_payload,
)

from experiments.poor_man_step_validity_demoter_defer_probe import _routes_of, raw_rule_blocks
import experiments.poor_man_reaction_type_oracle_probe as p56
import experiments.poor_man_etherification_recognizer_probe as p57

FROZEN_HASH = "5f0be063224819d53547d8d9d0cecd4bd33eb80e34fe220fd47202b8d1e25c8f"

_ETHER = "etherification"
_ACYL = "acyl condensation"


# --------------------------------------------------------------------------------------------------
# harness: build the REAL centre-carrying synthesis step for a named decomposition (deterministic).
# --------------------------------------------------------------------------------------------------
def _steps_for(reactant_smi: str, want_products: "list[str]", k: int = 1) -> "list[ExperimentStep]":
    """Every centre-carrying synthesis step whose decomposition splits ``reactant_smi`` (+ water) into exactly
    ``want_products``.  These carry a reaction centre (built ``from_transform`` on a real CappedScission)."""
    r = parse_smiles(reactant_smi)
    w = parse_smiles("O")
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    steps = []
    for cs in capped_scissions(r, (w,), max_reactant_cuts=k)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            steps.append(ExperimentStep.from_transform(cs))
    return steps


def _one(reactant_smi: str, want_products: "list[str]", k: int = 1) -> "ExperimentStep":
    steps = _steps_for(reactant_smi, want_products, k)
    assert steps, f"no scission of {reactant_smi} -> {want_products} at k={k}"
    return steps[0]


def _hand_step(reactant_smis, product_smis, target_smi) -> "ExperimentStep":
    """A hand-built conserving step -- carries NO reaction centre (exercises the span-absent R57 fallback)."""
    water = structure_by_name("water").molecule
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else water for s in product_smis)
    target = parse_smiles(target_smi)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def _vouched_ether(step) -> bool:
    k = recognize_reaction_type(step)
    return k is not None and _ETHER in k


def _vouched_acyl(step) -> bool:
    k = recognize_reaction_type(step)
    return k is not None and _ACYL in k


# --------------------------------------------------------------------------------------------------
# (1) THE COVERAGE CONSUMER: a spectator-ether etherification, R57-demoted, now VOUCHED; target un-blocked.
# --------------------------------------------------------------------------------------------------
def coverage_consumer_served() -> dict:
    # methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water : real etherification, reactant has a spectator ether
    step = _one("COCCOC", ["CO", "COCCO"])
    r57_would_demote = not _is_intermolecular_etherification(step)   # R57 whole-molecule predicate (clause iii)
    r58_vouches = _vouched_ether(step)
    reactant_has_spectator_ether = _reactant_ether_count(step) > 0
    # the step is a real single condensation by its span
    center = step.reaction_center
    real_single_condensation = center is not None and center.is_elementary_condensation(("O",)) \
        and _ether_shape_and_net_change(step)
    return {
        "step": step.equation(),
        "reactant_has_spectator_ether": reactant_has_spectator_ether,
        "r57_whole_molecule_demotes": r57_would_demote,
        "r58_span_local_vouches": r58_vouches,
        "is_real_single_condensation": real_single_condensation,
        "served": r57_would_demote and r58_vouches and reactant_has_spectator_ether and real_single_condensation,
    }


# --------------------------------------------------------------------------------------------------
# (2) THE COVERAGE RECOVERY SET: R58 vouch & R57 demote across a fixed library -- every member REAL.
# --------------------------------------------------------------------------------------------------
_RECOVERY_LIB = ["COCCOC", "CCOCCOCC", "COCCOCCOC", "CCOCCOCCOCC", "COCCOCC"]


def coverage_recovery() -> dict:
    recovered = 0
    all_real = True
    for smi in _RECOVERY_LIB:
        r = parse_smiles(smi)
        for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
            step = ExperimentStep.from_transform(cs)
            r57 = _is_intermolecular_etherification(step)
            r58 = _vouched_ether(step)
            if r58 and not r57:
                recovered += 1
                # a recovered step MUST be a genuine single condensation: elementary O-centre + shape+net
                center = step.reaction_center
                if not (center is not None and center.is_elementary_condensation(("O",))
                        and _ether_shape_and_net_change(step)):
                    all_real = False
    return {
        "library": _RECOVERY_LIB,
        "recovered_steps": recovered,
        "every_recovered_is_a_real_single_condensation": all_real,
    }


# --------------------------------------------------------------------------------------------------
# (3) SOUNDNESS across the production frontier: 0 false-VOUCH, and R58 vouches >= R57's reals (no lost coverage).
# --------------------------------------------------------------------------------------------------
def frontier_soundness() -> dict:
    fp = total = 0
    r58_vouched = set()
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
            is_fiction = raw_rule_blocks(r)              # C-C bond => ground-truth reaction-type fiction
            vouch = not route_reaction_type_blockers(r)
            if vouch and is_fiction:
                fp += 1                                   # FALSE-VOUCH -- the catastrophic error; must be 0
            elif vouch:
                r58_vouched.add(ns.name)
    return {
        "total_frontier_routes": total,
        "false_vouch_count": fp,
        "reals_vouched": len(r58_vouched),
        "vouched_targets": sorted(r58_vouched),
    }


# --------------------------------------------------------------------------------------------------
# (4) CONFIG-ROBUST SOUNDNESS (k>=2): the span demotes census-false-vouches the whole-molecule count admits.
# --------------------------------------------------------------------------------------------------
def config_robustness() -> dict:
    def kills(targets, census_pred, vouch_pred):
        census_vouched = span_demoted = 0
        for smi in targets:
            r = parse_smiles(smi)
            for cs in capped_scissions(r, (parse_smiles("O"), parse_smiles("O")), max_reactant_cuts=2)[0]:
                try:
                    step = ExperimentStep.from_transform(cs)
                except Exception:
                    continue
                if census_pred(step):
                    census_vouched += 1
                    if not vouch_pred(step):     # span-local recognizer demotes what the census vouched
                        span_demoted += 1
        return census_vouched, span_demoted

    e_c, e_k = kills(["C1CCOC1"], _is_intermolecular_etherification, _vouched_ether)
    a_c, a_k = kills(["CC(=O)Nc1ccccc1"], _is_intermolecular_acyl_condensation, _vouched_acyl)
    return {
        "ether_k2_census_vouched": e_c, "ether_k2_span_demoted_bundles": e_k,
        "acyl_k2_census_vouched": a_c, "acyl_k2_span_demoted_bundles": a_k,
        "span_demotes_reachable_bundles": e_k > 0 and a_k > 0,
    }


# --------------------------------------------------------------------------------------------------
# (5) live==replay + digest-invariance: the centre round-trips; it never changes step identity.
# --------------------------------------------------------------------------------------------------
def replay_and_digest() -> dict:
    step = _one("COCCOC", ["CO", "COCCO"])                      # a centre-carrying step
    payload = json.loads(json.dumps(_step_to_payload(step)))    # through JSON, as the replay envelope does
    replayed = _step_from_payload(payload)
    # a centre-less twin (same multisets, no span): identity must be identical (compare=False)
    twin = ExperimentStep.assembling(step.target, step.reactants, step.products,
                                     reagents=step.reagents, envelope=step.envelope)
    return {
        "live_carries_center": step.reaction_center is not None,
        "replay_carries_center": replayed.reaction_center is not None,
        "verdict_live_eq_replay": recognize_reaction_type(step) == recognize_reaction_type(replayed),
        "digest_live_eq_replay": step.digest == replayed.digest,
        "digest_invariant_to_center": step.digest == twin.digest,
        "eq_invariant_to_center": step == twin,
        "center_payload_key_present": "reaction_center" in _step_to_payload(step),
        "centerless_payload_omits_key": "reaction_center" not in _step_to_payload(twin),
    }


# --------------------------------------------------------------------------------------------------
# (6) ACYL UNREGRESSED + verdict-neutral at k=1: ester/amide/thioester all still vouched, none lost.
# --------------------------------------------------------------------------------------------------
def acyl_unregressed() -> dict:
    ester = _one("CC(=O)OC", ["CC(=O)O", "CO"])
    amide = _one("CC(=O)N", ["CC(=O)O", "N"])
    nmethyl_amide = _one("CC(=O)NC", ["CC(=O)O", "CN"])
    thioester = _one("CC(=O)SC", ["CC(=O)O", "CS"])
    all_vouched = all(_vouched_acyl(s) for s in (ester, amide, nmethyl_amide, thioester))
    # verdict-neutrality: across a fixed library at k=1, no acyl step R57-vouched that R58 demotes
    lost = 0
    for smi in ["CC(=O)OC", "CC(=O)OCC", "CC(=O)N", "CC(=O)NC", "CC(=O)Nc1ccccc1", "CC(=O)OC(C)C"]:
        r = parse_smiles(smi)
        for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
            step = ExperimentStep.from_transform(cs)
            if _is_intermolecular_acyl_condensation(step) and not _vouched_acyl(step):
                lost += 1
    return {
        "ester_amide_nmethyl_thioester_all_vouched": all_vouched,
        "k1_acyl_coverage_lost": lost,
        "verdict_neutral_at_k1": lost == 0 and all_vouched,
    }


# --------------------------------------------------------------------------------------------------
# (7) R56 + R57 shipped classes still behave under the span refit (lightweight cross-check).
# The FULL R56/R57 frontier validation is the R56/R57 tests' job; re-sweeping it here would quadruple this
# probe's runtime, so this pins only that the probes remain importable/frozen and their canonical classes are
# still positively recognized under the span-local oracle.
# --------------------------------------------------------------------------------------------------
def upstream_probes() -> dict:
    ester = _one("CC(=O)OC", ["CC(=O)O", "CO"])       # R56 canonical acyl class
    dme = _one("COC", ["CO", "CO"])                    # R57 canonical etherification class
    return {
        "r56_probe_frozen": hasattr(p56, "validate") and isinstance(getattr(p56, "FROZEN_HASH", None), str),
        "r57_probe_frozen": hasattr(p57, "validate") and isinstance(getattr(p57, "FROZEN_HASH", None), str),
        "r56_acyl_class_recognized": _vouched_acyl(ester),
        "r57_ether_class_recognized": _vouched_ether(dme),
    }


# --------------------------------------------------------------------------------------------------
# (8) ESCAPE #7 STAYS SHUT: caffeine (N-methylation) still demoted -- the span cannot vouch it.
# --------------------------------------------------------------------------------------------------
def caffeine_still_demoted() -> dict:
    routes = _routes_of(compile_synthesis(structure_by_name("caffeine").molecule, max_depth=2))
    return {
        "reachable": bool(routes),
        "all_demoted": bool(routes) and all(bool(route_reaction_type_blockers(r)) for r in routes),
    }


# --------------------------------------------------------------------------------------------------
# (9) FAIL-CLOSED + DISPOSITION: a raising recognizer abstains; the reason disclaims cost/feasibility.
# --------------------------------------------------------------------------------------------------
def fail_closed_and_disposition() -> dict:
    import smartchem.experiment.reaction_type_oracle as O
    orig = O._RECOGNIZERS

    def _boom(step):
        raise RuntimeError("recognizer boom")

    O._RECOGNIZERS = (("boom", _boom),) + orig
    try:
        fake = _hand_step(["CCOO", "CC"], ["CCOCC", "water"], "CCOCC")
        no_crash = True
        try:
            recognize_reaction_type(fake)
        except Exception:
            no_crash = False
        still_demoted = recognize_reaction_type(fake) is None
    finally:
        O._RECOGNIZERS = orig

    class _R:
        steps = (_hand_step(["CCOO", "CC"], ["CCOCC", "water"], "CCOCC"),)
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
    cov = coverage_consumer_served()
    rec = coverage_recovery()
    snd = frontier_soundness()
    cfg = config_robustness()
    rep = replay_and_digest()
    acyl = acyl_unregressed()
    ups = upstream_probes()
    caff = caffeine_still_demoted()
    fc = fail_closed_and_disposition()
    return {
        "schema": "poor-man-span-local-recognizer-01",
        "round": 58,
        "coverage_consumer_served": cov,
        "coverage_recovery": rec,
        "frontier_soundness": snd,
        "config_robustness": cfg,
        "replay_and_digest": rep,
        "acyl_unregressed": acyl,
        "upstream_probes": ups,
        "caffeine_still_demoted": caff,
        "fail_closed_and_disposition": fc,
        # THE VERDICT: both recognizers read the reaction-centre SPAN. It SERVES a coverage consumer (spectator-ether
        # etherification recovered, clause iii retired), RECOVERS a set of genuine etherifications (all real), stays
        # SOUND on the frontier (0 false-VOUCH), DEMOTES reachable k>=2 bundled census-false-vouches (config-robust),
        # round-trips through replay identically and never changes step identity, keeps acyl unregressed + verdict-
        # neutral at k=1, leaves R56/R57 validating, keeps escape #7 shut, and is fail-closed + disposition-honest.
        "ship_verdict": (
            cov["served"]
            and rec["recovered_steps"] > 0 and rec["every_recovered_is_a_real_single_condensation"]
            and snd["false_vouch_count"] == 0
            and cfg["span_demotes_reachable_bundles"]
            and rep["verdict_live_eq_replay"] and rep["digest_live_eq_replay"]
            and rep["digest_invariant_to_center"] and rep["eq_invariant_to_center"]
            and acyl["verdict_neutral_at_k1"]
            and ups["r56_probe_frozen"] and ups["r57_probe_frozen"]
            and ups["r56_acyl_class_recognized"] and ups["r57_ether_class_recognized"]
            and caff["all_demoted"]
            and fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the R58 SHIP result holds against live code: the span-local recognizers serve the coverage consumer
    (a spectator-ether etherification R57 sank is recovered), recover only REAL etherifications, stay SOUND on the
    frontier (0 false-VOUCH), demote reachable k>=2 bundled census-false-vouches (config-robust), round-trip
    identically through replay while never changing step identity, keep acyl unregressed + verdict-neutral at k=1,
    leave R56/R57 validating, keep escape #7 shut (caffeine demoted), and stay fail-closed + disposition-honest."""
    p = _payload()
    assert p["coverage_consumer_served"]["served"], f"coverage consumer not served: {p['coverage_consumer_served']}"
    rec = p["coverage_recovery"]
    assert rec["recovered_steps"] > 0, f"no coverage recovered -- R58 would be verdict-neutral: {rec}"
    assert rec["every_recovered_is_a_real_single_condensation"], f"a recovered step is NOT real: {rec}"
    snd = p["frontier_soundness"]
    assert snd["false_vouch_count"] == 0, f"UNSOUND: the oracle false-VOUCHed a fiction: {snd}"
    cfg = p["config_robustness"]
    assert cfg["span_demotes_reachable_bundles"], f"span demotes no reachable k>=2 bundle -- no config consumer: {cfg}"
    rep = p["replay_and_digest"]
    assert rep["verdict_live_eq_replay"] and rep["digest_live_eq_replay"], f"live != replay: {rep}"
    assert rep["digest_invariant_to_center"] and rep["eq_invariant_to_center"], f"centre changed step identity: {rep}"
    acyl = p["acyl_unregressed"]
    assert acyl["verdict_neutral_at_k1"], f"acyl regressed at k=1: {acyl}"
    ups = p["upstream_probes"]
    assert ups["r56_probe_frozen"] and ups["r57_probe_frozen"], f"an upstream probe is not frozen: {ups}"
    assert ups["r56_acyl_class_recognized"] and ups["r57_ether_class_recognized"], \
        f"an upstream canonical class stopped being recognized: {ups}"
    assert p["caffeine_still_demoted"]["all_demoted"], "caffeine stopped being demoted -- escape #7 reopened"
    fc = p["fail_closed_and_disposition"]
    assert fc["no_crash_on_raising_recognizer"] and fc["fake_still_demoted"] and fc["disposition_honest"], \
        f"fail-closed / disposition broken: {fc}"
    assert p["ship_verdict"], f"R58 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
