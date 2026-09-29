"""POOR-MAN-TAMPER-HARDENING-01: the R59 disposition serialized-tamper forgery is closed on load.

The committed probe (:mod:`experiments.poor_man_tamper_hardening_probe`) is the frozen evidence; these are the fast
regression pins over the SAME live behaviour, kept independent of the probe so a refactor cannot silently reopen the
hole.  The load-bearing pin is :func:`test_the_reproduced_hard_tamper_is_refused_on_load` -- the EXACT reproduction the
reviewer replays: strip ``hard_blockers`` off a REAL_BUT_HARD frontier entry, and the round-trip must now RAISE.
"""
from __future__ import annotations

import copy

import pytest

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.process_constraints import ProcessBounds
from smartchem.service import (
    COMPILATION_RESPONSE_SCHEMA, build_recompile_request, run_compilation,
    response_to_payload, response_from_payload,
)
import experiments.poor_man_tamper_hardening_probe as probe

_KITCHEN = ("stovetop", "pot", "glass jar", "thermometer", "spoon", "funnel")


def _bounded_payload():
    resp = run_compilation(build_recompile_request(
        "isopentyl acetate", max_depth=3, stock_materials=("isopentyl alcohol", "acetic acid"),
        process=ProcessBounds(available_equipment=_KITCHEN)))
    return response_to_payload(resp, include_replay=True)


def _unbounded_payload():
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    return response_to_payload(resp, include_replay=True)


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_reproduced_hard_tamper_is_refused_on_load():
    # the EXACT reproduction: a REAL_BUT_HARD entry, hard_blockers stripped (disposition would flip to CLEAN), the
    # result_digest byte-identical -- and the round-trip under verified admission now RAISES.
    honest = _bounded_payload()
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr)
             if e["cost_vector"]["hard_blockers"] and not e["cost_vector"]["fiction_blockers"])
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["hard_blockers"] = []
    assert tampered["result_digest"] == honest["result_digest"]      # the hole's root: frontier is digest-excluded
    response_from_payload(copy.deepcopy(honest), require_verified_admission=True)   # honest loads
    with pytest.raises(ValueError):
        response_from_payload(tampered, require_verified_admission=True)


def test_the_hard_tamper_is_refused_even_without_verified_admission():
    # the guard rides response_from_payload (the deserialization seam), unconditional on require_verified_admission --
    # so a bare load still refuses the process-exclusion strip (that channel needs no replay).
    honest = _bounded_payload()
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["hard_blockers"])
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["hard_blockers"] = []
    with pytest.raises(ValueError):
        response_from_payload(tampered)


def test_the_fiction_tamper_is_refused_on_load():
    honest = _unbounded_payload()
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    with pytest.raises(ValueError):
        response_from_payload(tampered, require_verified_admission=True)


def test_the_centre_null_fiction_evasion_is_refused():
    # the two-step evasion: strip fiction_blockers AND null the replay centres so the oracle would census-vouch on
    # reload.  PIECE 2 fails closed on an absent centre, so the fiction re-derives and the tamper is still refused.
    honest = _unbounded_payload()
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    rd = fr[i]["route_digest"]
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    for d in tampered["ranked_route_dossiers"]:
        if d["route_digest"] == rd and d.get("replay_payload"):
            for sp in d["replay_payload"]:
                sp.pop("reaction_center", None)
    with pytest.raises(ValueError):
        response_from_payload(tampered, require_verified_admission=True)


def test_a_substituted_replay_under_a_stripped_entry_is_refused():
    # KILL 1 (gate finding): strip an entry's fiction_blockers AND overwrite its matched summary's replay with a
    # DIFFERENT recognized route's replay.  The re-derivation reconstructs the wrong route (digest != entry) -> refused.
    honest = _unbounded_payload()
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    fic_rd = fr[i]["route_digest"]
    donor_rd = next(e["route_digest"] for e in fr if e["route_digest"] != fic_rd)
    donor_replay = next(d["replay_payload"] for d in honest["ranked_route_dossiers"] if d["route_digest"] == donor_rd)
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    for d in tampered["ranked_route_dossiers"]:
        if d["route_digest"] == fic_rd:
            d["replay_payload"] = copy.deepcopy(donor_replay)
    with pytest.raises(ValueError):
        response_from_payload(tampered, require_verified_admission=True)


def test_a_frontier_entry_whose_dossier_is_deleted_is_refused():
    # evil-morty CRITICAL (the fail-open the first thin-transport-closure attempt left open): strip fiction_blockers
    # AND DELETE the entry's matching ranked_route_dossier, so the entry would hit the `summary is None` path and skip
    # ALL disposition re-derivation -> a forged NOT_A_REACTION->CLEAN loaded.  The __post_init__ FRONTIER<=DOSSIERS
    # guard now refuses it at construction, UNCONDITIONALLY -- so it is caught under verified admission, on a bare
    # load, and on the thin transport alike (the guard is transport- and mode-agnostic; no dossier == unverifiable).
    honest = _unbounded_payload()                                    # thick
    fr = honest["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    rd = fr[i]["route_digest"]
    tampered = copy.deepcopy(honest)
    tampered["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    tampered["ranked_route_dossiers"] = [d for d in tampered["ranked_route_dossiers"] if d["route_digest"] != rd]
    with pytest.raises(ValueError, match="frontier<=dossiers|no matching|UNVERIFIABLE|dossier"):
        response_from_payload(tampered, require_verified_admission=True)          # verified admission
    with pytest.raises(ValueError, match="frontier<=dossiers|no matching|UNVERIFIABLE|dossier"):
        response_from_payload(copy.deepcopy(tampered))                            # bare load -- guard is unconditional


def test_a_thin_frontier_entry_whose_dossier_is_deleted_is_refused():
    # the same dossier-deletion tamper on the DEFAULT thin transport (no replay): still refused by FRONTIER<=DOSSIERS,
    # so the forgery cannot hide behind the replay-absent skip either.
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    thin = response_to_payload(resp, include_replay=False)           # v0.8 D5: the EXPLICIT thin opt-out (no replay)
    fr = thin["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    rd = fr[i]["route_digest"]
    thin["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    thin["ranked_route_dossiers"] = [d for d in thin["ranked_route_dossiers"] if d["route_digest"] != rd]
    with pytest.raises(ValueError, match="frontier<=dossiers|no matching|UNVERIFIABLE|dossier"):
        response_from_payload(thin, require_verified_admission=True)


def test_the_honest_payload_still_loads():
    # no false positives: a genuine response round-trips cleanly on both frontiers.
    response_from_payload(_bounded_payload(), require_verified_admission=True)
    response_from_payload(_unbounded_payload(), require_verified_admission=True)


@pytest.mark.parametrize("target", ["smiles:CC(=O)OC", "dimethyl ether", "caffeine"])
def test_each_recognizer_class_round_trips_thick_without_false_reject(target):
    # centre-round-trip fidelity (guards the coupling the fiction re-derivation leans on): a recognized route of each
    # class -- acyl (methyl acetate), ether (dimethyl ether), N-methyl (caffeine) -- must survive
    # response_to_payload(include_replay=True) -> response_from_payload with NO false-reject.  If the reaction centre
    # did not round-trip, the recognized step would DEMOTE on reload and _check_frontier_coherence would wrongly raise.
    resp = run_compilation(build_recompile_request(target, max_depth=3))
    assert any(not e.cost_vector.fiction_blockers for e in resp.affordability_frontier), \
        f"{target} has no vouched (fiction-free) frontier route -- the round-trip pin would be vacuous"
    thick = response_to_payload(resp, include_replay=True)
    response_from_payload(thick, require_verified_admission=True)     # must not false-reject


def test_the_default_thin_transport_fiction_strip_is_refused_under_verified_admission():
    # THE BOUNDARY, NOW CLOSED (thin-transport closure).  On the DEFAULT (thin) transport the replay is omitted, so the
    # fiction channel has no evidence to re-derive.  Rather than trust the unverifiable claim (the old fail-OPEN
    # boundary), a verified-admission load now fails CLOSED: an entry whose summary carries no replay_payload is
    # UNVERIFIED and REFUSED -- replay-MANDATORY-for-disposition-claims, mirroring _check_verified_admission's own
    # FITS-route rule.  So the fiction_blockers strip below is refused even though the replay is absent.
    from smartchem.service import _payload_body_digest, _transport_bound_result_digest
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    thin = response_to_payload(resp, include_replay=False)            # v0.8 D5: the EXPLICIT thin opt-out (no replay)
    fr = thin["affordability_frontier"]
    i = next(j for j, e in enumerate(fr) if e["cost_vector"]["fiction_blockers"])
    thin["affordability_frontier"][i]["cost_vector"]["fiction_blockers"] = []
    # X-high D27.2: the wire digest now covers the frontier, so the keyless forger recomputes it (otherwise the cheaper
    # digest-mismatch guard catches the strip before the thin-transport closure this test pins).
    thin["result_digest"] = _transport_bound_result_digest(resp.result_digest, thin["transport_mode"],
                                                           _payload_body_digest(thin))
    with pytest.raises(ValueError, match="no replay_payload|UNVERIFIED|thin-transport"):
        response_from_payload(thin, require_verified_admission=True)


def test_a_thin_transport_load_without_verified_admission_still_loads():
    # THE PRESERVED ADVISORY PATH: a bare (non-verified) load of a thin payload is NOT promised re-derivation, so it
    # still loads -- the thin frontier's catalyst/fiction dispositions stay producer-declared for that consumer.  This
    # pins that the closure is scoped to verified admission and did not break the default lightweight transport.
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    thin = response_to_payload(resp, include_replay=False)            # v0.8 D5: the EXPLICIT thin opt-out (no replay)
    assert any(e["cost_vector"]["fiction_blockers"] for e in thin["affordability_frontier"]), \
        "the frontier must carry a fiction disposition for this pin to be non-vacuous"
    response_from_payload(thin)                                       # bare load: no verified admission -> no refusal


def test_centre_absent_acyl_and_ether_now_fail_closed():
    # PIECE 2: a centre-less acyl or ether step demotes (was census-vouched); centre-carrying forms still vouch.
    water = structure_by_name("water").molecule

    def hand(r, p, t):
        rs = tuple(parse_smiles(s) for s in r)
        ps = tuple(parse_smiles(s) if s != "water" else water for s in p)
        tg = parse_smiles(t)
        tt = next((x for x in ps if dict(x.formula) == dict(tg.formula) and x.charge == tg.charge), ps[0])
        return ExperimentStep(STEP_SCHEMA, target=tt, reactants=rs, products=ps,
                              reagents=(), envelope=ConditionEnvelope.unknown())

    assert recognize_reaction_type(hand(["CC(=O)O", "CO"], ["CC(=O)OC", "water"], "CC(=O)OC")) is None
    assert recognize_reaction_type(hand(["CO", "CO"], ["COC", "water"], "COC")) is None
    assert probe._recognized(probe._derive_step("CC(=O)OC", ["CC(=O)O", "CO"])) is not None
    assert probe._recognized(probe._derive_step("COC", ["CO", "CO"])) is not None


def test_a_pre_hardening_schema_payload_is_refused():
    # the schema bump makes the load a hard refusal: a v1alpha12 (pre-guarantee) payload no longer loads.
    honest = _bounded_payload()
    assert honest["schema_version"] == COMPILATION_RESPONSE_SCHEMA
    stale = copy.deepcopy(honest)
    stale["schema_version"] = "smartchem.service/compilation-response-v1alpha12"
    with pytest.raises(ValueError):
        response_from_payload(stale)
