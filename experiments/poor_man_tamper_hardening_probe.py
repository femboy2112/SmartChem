"""POOR-MAN-TAMPER-HARDENING-01: close the R59 disposition SERIALIZED-TAMPER forgery, cheaply and honestly.

THE HOLE (proven, reproduced below).  The section-10.4 affordability frontier is DELIBERATELY EXCLUDED from
``CompilationResponse.result_digest`` (a price is dated data, not search identity), and until now no load-time guard
re-derived it.  So a hand-edited serialized response could STRIP a frontier entry's ``hard_blockers`` (or
``fiction_blockers``) and the entry's :class:`~smartchem.experiment.affordability.Disposition` would flip UP to a
better tier -- REAL_BUT_HARD or NOT_A_REACTION silently becoming CLEAN -- with ``result_digest`` byte-IDENTICAL and
every other coherence gate silent.  The disposition IS the ranking answer (a lower tier dominates cost at any price),
so that is a forged verdict.  A prior probe verified the REAL_BUT_HARD->CLEAN case live: strip ``hard_blockers`` off
an isopentyl-acetate/kitchen-bench REAL_BUT_HARD entry, round-trip via
``response_from_payload(tampered, require_verified_admission=True)`` -> NO exception, ``result_digest`` unchanged,
disposition CLEAN.

TWO COHERENT INCISIONS, NO R58 REVERSAL, NO ROUTE/STEP HASH BREAK:

  PIECE 1 -- ``CompilationResponse._check_frontier_coherence`` (service.py), invoked from ``response_from_payload``
  (the deserialization seam, after ``_check_verified_admission``; NOT ``__post_init__``).  For each frontier entry it
  RE-DERIVES the blockers ``_affordability_frontier`` itself computes -- ``hard_blockers`` from the digest-covered
  per-step ``process_requirements`` (process exclusions) plus ``route_catalyst_blockers`` over the route reconstructed
  from the thick replay payload, and ``fiction_blockers`` from ``route_reaction_type_blockers`` over that route -- and
  REFUSES (fail-closed, one-directional) any entry whose claimed blockers are LOOSER than the re-derivation.  KILL 1:
  the reconstructed route is DIGEST-BOUND to the entry (``route.digest == e.route_digest`` or raise), so a substituted
  replay cannot re-derive zero blockers under a stripped entry.  An honest response is self-consistent and passes.

  SCOPE (honest, bounded).  FULLY closed on EVERY transport: the process-exclusion ``hard_blockers`` channel (no replay
  needed).  FULLY closed on the THICK transport (``include_replay=True``, digest-bound): catalyst + fiction.  The
  DEFAULT THIN transport omits the replay, so a ``fiction_blockers`` strip there is ADVISORY (not detected) -- a
  deliberate, tracked boundary, pinned below, NOT a claimed closure.

  PIECE 2 -- the reaction-TYPE oracle's ``_acyl_condensation`` and ``_etherification`` now FAIL CLOSED on an absent
  reaction centre (``center is None -> return False``), extending the R60 N-methylation gate finding to the other two
  recognizers.  A tamperer who NULLS ``reaction_center`` in a replay payload therefore gets the step DEMOTED
  (unrecognized -> fiction_blocker), never census-only VOUCHED -- so centre-omission can only cause false-EXCLUDE
  (safe), never false-VOUCH (catastrophic).  This defuses the fiction channel WITHOUT digest-binding the centre (no R58
  reversal), and en passant closes the pre-existing acyl/ether centre-absent homologation debt.

THIS PROBE FREEZES, against LIVE code:
  (1) the HARD tamper reproduced-then-REFUSED: ``result_digest`` invariant under the strip (the hole's root), the
      honest disposition REAL_BUT_HARD, the stripped CostVector's disposition CLEAN (the forged verdict), the honest
      payload loads, the tampered one is REFUSED on load.
  (2) the FICTION tamper reproduced-then-REFUSED, and the two-step CENTRE-NULL evasion (strip fiction_blockers AND null
      the replay centres) also REFUSED end-to-end.
  (3) KILL 1 -- a SUBSTITUTED replay (a DIFFERENT recognized route's payload swapped under a stripped entry's digest)
      REFUSED, via the ``route.digest == e.route_digest`` bind.
  (4) THE DEFAULT-TRANSPORT BOUNDARY, pinned NOT hidden: a thin (no-replay) fiction strip LOADS (advisory) -- the
      honest edge a future thin-transport-closure round trips green.
  (5) the PIECE-2 unit facts: acyl/ether/N-methylation centre-LESS steps all DEMOTE while their centre-CARRYING forms
      VOUCH, and the sharp evasion case -- a k=2 bundle the CENSUS vouches but the SPAN demotes -- whose centre-less
      twin now FAILS CLOSED (pre-hardening it census-vouched).
  (6) the RESIDUAL boundary, stated not hidden: ``result_digest`` does not cover the frontier, so a fully-coherent
      forger who FABRICATES a self-consistent replay is indistinguishable from honest at this structural layer -- that
      needs HMAC signing (COMBINED-VERDICT-AUTH), out of scope.  The honest self-consistent response loads, as it must.
"""
from __future__ import annotations

import copy
import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.affordability import Disposition, CostVector
from smartchem.experiment.feasibility import _ether_shape_and_net_change
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.process_constraints import ProcessBounds
from smartchem.service import (
    build_recompile_request, run_compilation, response_to_payload, response_from_payload,
)

FROZEN_HASH = "c3839f7a837a79676c8437d93180ef16c9bf175ac93d7a328b5a961477ab5ebe"

#: a poor-man kitchen inventory that LACKS lab glassware -> the Fischer esterification is process-EXCLUDED (REAL_BUT_HARD).
_KITCHEN = ("stovetop", "pot", "glass jar", "thermometer", "spoon", "funnel")
_TARGET = "isopentyl acetate"
_STOCK = ("isopentyl alcohol", "acetic acid")

_CACHE: "dict[str, object]" = {}


def _bounded_payload() -> dict:
    """The serialized (replay-carrying) response for the flagship REAL_BUT_HARD scenario -- built once."""
    if "bounded" not in _CACHE:
        resp = run_compilation(build_recompile_request(
            _TARGET, max_depth=3, stock_materials=_STOCK,
            process=ProcessBounds(available_equipment=_KITCHEN)))
        _CACHE["bounded"] = response_to_payload(resp, include_replay=True)
    return copy.deepcopy(_CACHE["bounded"])


def _unbounded_payload() -> dict:
    """The serialized (replay-carrying) response whose UNBOUNDED frontier carries NOT_A_REACTION fictions."""
    if "unbounded" not in _CACHE:
        resp = run_compilation(build_recompile_request(_TARGET, max_depth=3))
        _CACHE["unbounded"] = response_to_payload(resp, include_replay=True)
    return copy.deepcopy(_CACHE["unbounded"])


def _refused(payload: dict) -> bool:
    """True iff loading ``payload`` under verified admission is REFUSED (a ValueError is raised)."""
    try:
        response_from_payload(payload, require_verified_admission=True)
        return False
    except ValueError:
        return True


def _loads(payload: dict) -> bool:
    try:
        response_from_payload(payload, require_verified_admission=True)
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------------------------------
# (1) THE HARD TAMPER: REAL_BUT_HARD -> CLEAN, digest-invariant, reproduced then REFUSED.
# --------------------------------------------------------------------------------------------------
def hard_tamper_reproduced_then_refused() -> dict:
    honest = _bounded_payload()
    fr = honest["affordability_frontier"]
    rbh = [i for i, e in enumerate(fr)
           if e["cost_vector"]["hard_blockers"] and not e["cost_vector"]["fiction_blockers"]]
    i = rbh[0]
    honest_hard = tuple(fr[i]["cost_vector"]["hard_blockers"])
    # the honest entry's disposition, and the disposition the STRIPPED CostVector would carry (the forged verdict)
    honest_disp = CostVector(hard_blockers=honest_hard).disposition
    stripped_disp = CostVector(hard_blockers=()).disposition
    tampered = _bounded_payload()
    tampered["affordability_frontier"][i]["cost_vector"]["hard_blockers"] = []
    return {
        "real_but_hard_entry_present": bool(rbh),
        "result_digest_invariant_under_tamper": tampered["result_digest"] == honest["result_digest"],
        "honest_disposition_is_real_but_hard": honest_disp is Disposition.REAL_BUT_HARD,
        "stripped_disposition_is_clean": stripped_disp is Disposition.CLEAN,
        "honest_payload_loads": _loads(honest),
        "hard_tamper_refused": _refused(tampered),
    }


# --------------------------------------------------------------------------------------------------
# (2) THE FICTION TAMPER: NOT_A_REACTION -> CLEAN, reproduced then REFUSED (incl. the centre-null evasion).
# --------------------------------------------------------------------------------------------------
def fiction_tamper_reproduced_then_refused() -> dict:
    honest = _unbounded_payload()
    fr = honest["affordability_frontier"]
    fic = [i for i, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"]]
    i = fic[0]
    rd = fr[i]["route_digest"]
    strip = _unbounded_payload()
    strip["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    # the two-step evasion: ALSO null every reaction centre in that route's replay (PIECE 2 must still catch it)
    evade = _unbounded_payload()
    evade["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    for d in evade["ranked_route_dossiers"]:
        if d["route_digest"] == rd and d.get("replay_payload"):
            for sp in d["replay_payload"]:
                sp.pop("reaction_center", None)
    return {
        "fiction_entry_present": bool(fic),
        "result_digest_invariant_under_tamper": strip["result_digest"] == honest["result_digest"],
        "honest_payload_loads": _loads(honest),
        "fiction_tamper_refused": _refused(strip),
        "centre_null_evasion_refused": _refused(evade),
    }


# --------------------------------------------------------------------------------------------------
# (3) PIECE 2 UNIT FACTS: centre-absent recognizers fail closed; the census/span evasion is shut.
# --------------------------------------------------------------------------------------------------
def _water():
    return structure_by_name("water").molecule


def _hand_step(reactant_smis, product_smis, target_smi) -> "ExperimentStep":
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else _water() for s in product_smis)
    target = parse_smiles(target_smi)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def _derive_step(product_smiles, want_products, k: int = 1):
    r = parse_smiles(product_smiles)
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    for cs in capped_scissions(r, tuple(parse_smiles("O") for _ in range(k)), max_reactant_cuts=k)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    return None


def _recognized(step) -> "str | None":
    return recognize_reaction_type(step) if step is not None else None


def centre_absent_is_fail_closed() -> dict:
    acyl_less = _recognized(_hand_step(["CC(=O)O", "CO"], ["CC(=O)OC", "water"], "CC(=O)OC"))
    ether_less = _recognized(_hand_step(["CO", "CO"], ["COC", "water"], "COC"))
    nmethyl_less = _recognized(_hand_step(["Nc1ccccc1", "CO"], ["CNc1ccccc1", "water"], "CNc1ccccc1"))
    acyl_full = _recognized(_derive_step("CC(=O)OC", ["CC(=O)O", "CO"]))
    ether_full = _recognized(_derive_step("COC", ["CO", "CO"]))
    # the sharp evasion: a k=2 bundle the CENSUS vouches but the SPAN demotes; its centre-less twin now fails closed
    census_vouch_span_demote = False
    centreless_twin_fails_closed = False
    for cs in capped_scissions(parse_smiles("C1CCOC1"),
                               (parse_smiles("O"), parse_smiles("O")), max_reactant_cuts=2)[0]:
        try:
            step = ExperimentStep.from_transform(cs)
        except Exception:
            continue
        if _ether_shape_and_net_change(step) and recognize_reaction_type(step) is None:
            census_vouch_span_demote = True
            twin = ExperimentStep.assembling(step.target, step.reactants, step.products,
                                             reagents=step.reagents, envelope=step.envelope)
            # census STILL vouches the centre-less twin, but the recognizer now DEMOTES it (pre-hardening: vouched)
            centreless_twin_fails_closed = (
                twin.reaction_center is None
                and _ether_shape_and_net_change(twin)
                and recognize_reaction_type(twin) is None
            )
            break
    return {
        "acyl_centreless_demoted": acyl_less is None,
        "ether_centreless_demoted": ether_less is None,
        "nmethyl_centreless_demoted": nmethyl_less is None,
        "acyl_centre_carrying_vouched": acyl_full is not None and "acyl" in acyl_full,
        "ether_centre_carrying_vouched": ether_full is not None and "etherification" in ether_full,
        "census_vouch_span_demote_bundle_present": census_vouch_span_demote,
        "centreless_twin_fails_closed": centreless_twin_fails_closed,
    }


# --------------------------------------------------------------------------------------------------
# (4) KILL 1: a SUBSTITUTED replay (a different recognized route's payload under this entry's digest) is REFUSED.
# --------------------------------------------------------------------------------------------------
def kill1_substitution_refused() -> dict:
    honest = _unbounded_payload()
    fr = honest["affordability_frontier"]
    fic = [i for i, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"]]
    donors = [i for i, e in enumerate(fr) if fr[i]["route_digest"] != fr[fic[0]]["route_digest"]]
    i, donor = fic[0], donors[0]
    fic_rd = fr[i]["route_digest"]
    donor_rd = fr[donor]["route_digest"]
    donor_replay = next(d["replay_payload"] for d in honest["ranked_route_dossiers"]
                        if d["route_digest"] == donor_rd)
    sub = _unbounded_payload()
    sub["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []      # strip the fiction ...
    for d in sub["ranked_route_dossiers"]:
        if d["route_digest"] == fic_rd:
            d["replay_payload"] = copy.deepcopy(donor_replay)                     # ... and substitute a DIFFERENT route
    return {
        "distinct_donor_present": donor_rd != fic_rd,
        "substitution_refused": _refused(sub),
    }


# --------------------------------------------------------------------------------------------------
# (5) THE DEFAULT-TRANSPORT BOUNDARY (honest, pinned NOT hidden): a thin (no-replay) fiction strip is ADVISORY.
# --------------------------------------------------------------------------------------------------
def thin_transport_fiction_is_advisory() -> dict:
    resp = run_compilation(build_recompile_request(_TARGET, max_depth=3))
    thin = response_to_payload(resp)                 # include_replay defaults False -> no replay on the wire
    fr = thin["affordability_frontier"]
    fic = [i for i, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"]]
    strip = copy.deepcopy(thin)
    strip["affordability_frontier"][fic[0]]["cost_vector"]["fiction_blockers"] = []
    return {
        "fiction_entry_present": bool(fic),
        "thin_omits_replay": all(d.get("replay_payload") is None for d in thin["ranked_route_dossiers"]),
        # THE DOCUMENTED BOUNDARY: on the default thin transport the fiction channel has no evidence to re-derive,
        # so the strip LOADS.  Pinned True (not hidden) so a future thin-transport-closure round trips it.
        "thin_fiction_strip_loads": _loads(strip),
    }


# --------------------------------------------------------------------------------------------------
# (6) THE RESIDUAL BOUNDARY: the digest does not cover the frontier, so a self-consistent replay is trusted.
# --------------------------------------------------------------------------------------------------
def residual_boundary_stated() -> dict:
    honest = _bounded_payload()
    # touching a frontier reason string does NOT move result_digest -> the frontier is outside the identity, so only
    # the structural re-derivation (not a signature) guards it; a fabricated self-consistent replay is out of scope.
    probe = _bounded_payload()
    fr = probe["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["hard_blockers"])
    probe["affordability_frontier"][i]["cost_vector"]["region"] = "TAMPERED-METADATA"
    return {
        "result_digest_excludes_the_frontier": probe["result_digest"] == honest["result_digest"],
        "honest_self_consistent_replay_loads": _loads(honest),
    }


def _payload() -> dict:
    hard = hard_tamper_reproduced_then_refused()
    fic = fiction_tamper_reproduced_then_refused()
    kill1 = kill1_substitution_refused()
    thin = thin_transport_fiction_is_advisory()
    unit = centre_absent_is_fail_closed()
    resid = residual_boundary_stated()
    return {
        "schema": "poor-man-tamper-hardening-01",
        "hard_tamper": hard,
        "fiction_tamper": fic,
        "kill1_substitution": kill1,
        "thin_transport_boundary": thin,
        "centre_absent_fail_closed": unit,
        "residual_boundary": resid,
        # THE VERDICT: both channels of the R59 forgery are closed on load -- the PROVEN REAL_BUT_HARD->CLEAN strip
        # (digest-invariant, now refused), the NOT_A_REACTION->CLEAN strip and its centre-null evasion (refused), the
        # centre-absent recognizers fail closed while centre-carrying ones vouch, and the residual (a fabricated
        # self-consistent replay) is honestly stated as the HMAC boundary.
        "ship_verdict": (
            hard["real_but_hard_entry_present"]
            and hard["result_digest_invariant_under_tamper"]
            and hard["honest_disposition_is_real_but_hard"] and hard["stripped_disposition_is_clean"]
            and hard["honest_payload_loads"] and hard["hard_tamper_refused"]
            and fic["fiction_entry_present"] and fic["honest_payload_loads"]
            and fic["fiction_tamper_refused"] and fic["centre_null_evasion_refused"]
            and kill1["distinct_donor_present"] and kill1["substitution_refused"]
            and thin["fiction_entry_present"] and thin["thin_omits_replay"]
            and thin["thin_fiction_strip_loads"]
            and unit["acyl_centreless_demoted"] and unit["ether_centreless_demoted"]
            and unit["nmethyl_centreless_demoted"]
            and unit["acyl_centre_carrying_vouched"] and unit["ether_centre_carrying_vouched"]
            and unit["census_vouch_span_demote_bundle_present"] and unit["centreless_twin_fails_closed"]
            and resid["result_digest_excludes_the_frontier"] and resid["honest_self_consistent_replay_loads"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert TAMPER-HARDENING-01 against live code: the R59 disposition serialized-tamper is closed on BOTH channels
    (the proven REAL_BUT_HARD->CLEAN hard strip, and the NOT_A_REACTION->CLEAN fiction strip plus its centre-null
    evasion), the digest is invariant under the strip (the hole's root), the centre-absent recognizers fail closed
    while centre-carrying ones vouch, and the residual (a fabricated self-consistent replay) is the stated HMAC
    boundary."""
    p = _payload()
    h = p["hard_tamper"]
    assert h["result_digest_invariant_under_tamper"], f"the frontier is inside result_digest?! {h}"
    assert h["honest_disposition_is_real_but_hard"] and h["stripped_disposition_is_clean"], \
        f"the tamper does not flip REAL_BUT_HARD->CLEAN -- re-state the hole: {h}"
    assert h["honest_payload_loads"], f"the HONEST bounded payload is refused (a false positive): {h}"
    assert h["hard_tamper_refused"], f"HOLE OPEN: the REAL_BUT_HARD->CLEAN strip loaded: {h}"
    f = p["fiction_tamper"]
    assert f["honest_payload_loads"], f"the HONEST unbounded payload is refused (a false positive): {f}"
    assert f["fiction_tamper_refused"], f"HOLE OPEN: the NOT_A_REACTION->CLEAN strip loaded: {f}"
    assert f["centre_null_evasion_refused"], f"HOLE OPEN: the centre-null fiction evasion loaded: {f}"
    k = p["kill1_substitution"]
    assert k["distinct_donor_present"], f"the KILL 1 substitution setup is degenerate (no distinct donor): {k}"
    assert k["substitution_refused"], f"KILL 1 OPEN: a substituted replay under a stripped entry loaded: {k}"
    t = p["thin_transport_boundary"]
    assert t["thin_omits_replay"], f"the default thin transport unexpectedly carried a replay: {t}"
    # HONEST BOUNDARY (pinned True, not hidden): the thin-transport fiction strip is ADVISORY -- it LOADS.  A future
    # thin-transport-closure round flips this to refused; until then this asserts the boundary is exactly where stated.
    assert t["thin_fiction_strip_loads"], f"the thin-transport boundary moved -- re-state it (strip now refused?): {t}"
    u = p["centre_absent_fail_closed"]
    assert u["acyl_centreless_demoted"] and u["ether_centreless_demoted"] and u["nmethyl_centreless_demoted"], \
        f"a centre-less recognizer still vouches (PIECE 2 regressed): {u}"
    assert u["acyl_centre_carrying_vouched"] and u["ether_centre_carrying_vouched"], \
        f"a centre-carrying real reaction stopped being recognized: {u}"
    assert u["census_vouch_span_demote_bundle_present"] and u["centreless_twin_fails_closed"], \
        f"the census/span evasion demonstration broke: {u}"
    r = p["residual_boundary"]
    assert r["result_digest_excludes_the_frontier"], f"the frontier unexpectedly entered result_digest: {r}"
    assert r["honest_self_consistent_replay_loads"], f"the honest replay is refused: {r}"
    assert p["ship_verdict"], f"TAMPER-HARDENING-01 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
