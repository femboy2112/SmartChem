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
    # the guard rides __post_init__, so the tamper is caught at construction -- verified admission is not required.
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


def test_the_honest_payload_still_loads():
    # no false positives: a genuine response round-trips cleanly on both frontiers.
    response_from_payload(_bounded_payload(), require_verified_admission=True)
    response_from_payload(_unbounded_payload(), require_verified_admission=True)


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
