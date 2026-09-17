"""POOR-MAN-SPAN-LOCAL-RECOGNIZER-01 (R58): the recognizers read the rewrite MORPHISM, not a whole-molecule count.

The committed probe (:mod:`experiments.poor_man_span_local_recognizer_probe`) is the frozen evidence that carrying the
generator's reaction-centre span (:class:`smartchem.reaction_center.ReactionCenter`) onto the step and reading it in
the reaction-TYPE oracle (a) RECOVERS genuine etherifications the R57 whole-molecule "no reactant ether" clause
false-demoted (a production k=1 coverage consumer), (b) DEMOTES reachable k>=2 bundled census-false-vouches
(config-robust soundness), and (c) never changes step identity (the centre is digest-invisible and round-trips
through replay).

These are the fast regression pins over the SAME live behaviour, independent of the probe.  If the "consumer" pin
stops firing, the span-local recovery broke (re-state the win).  If the "soundness" pin stops firing, the oracle
started false-VOUCHing (the catastrophic regression -- STOP).  If a "config-robustness" pin stops firing, the span
elementarity clause was weakened.  If a "digest/replay" pin stops firing, the centre leaked into step identity.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.reaction_center import ReactionCenter, REACTION_CENTER_SCHEMA
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.feasibility import _is_intermolecular_etherification
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation, _step_to_payload, _step_from_payload
import experiments.poor_man_span_local_recognizer_probe as probe


def _one(reactant_smi, want):
    r = parse_smiles(reactant_smi)
    want_keys = sorted(parse_smiles(s).canonical().__repr__() for s in want)
    for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want_keys:
            return ExperimentStep.from_transform(cs)
    raise AssertionError(f"no scission {reactant_smi} -> {want}")


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_spectator_ether_etherification_is_recovered():
    # methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water: real, but the reactant has a spectator methoxy.
    step = _one("COCCOC", ["CO", "COCCO"])
    assert step.reaction_center is not None                       # carries the span
    assert _is_intermolecular_etherification(step) is False       # R57 whole-molecule predicate SANK it (clause iii)
    klass = recognize_reaction_type(step)
    assert klass is not None and "etherification" in klass        # R58 span-local RECOVERS it


def test_a_plain_etherification_is_still_recognized():
    step = _one("COC", ["CO", "CO"])                              # 2 methanol -> dimethyl ether + water
    klass = recognize_reaction_type(step)
    assert klass is not None and "etherification" in klass


def test_esterification_amidation_thioesterification_all_vouched():
    for reactant, want in (("CC(=O)OC", ["CC(=O)O", "CO"]),      # ester
                           ("CC(=O)N", ["CC(=O)O", "N"]),        # amide
                           ("CC(=O)SC", ["CC(=O)O", "CS"])):     # thioester
        step = _one(reactant, want)
        klass = recognize_reaction_type(step)
        assert klass is not None and "acyl condensation" in klass, f"{reactant} not vouched: {klass}"


def test_the_span_demotes_a_reachable_k2_bundled_census_false_vouch():
    # THF + 2 water -> (bundled) : the whole-molecule ether census false-vouches some k=2 bundle; the span demotes it.
    r = parse_smiles("C1CCOC1")
    census_vouched = span_demoted = 0
    for cs in capped_scissions(r, (parse_smiles("O"), parse_smiles("O")), max_reactant_cuts=2)[0]:
        try:
            step = ExperimentStep.from_transform(cs)
        except Exception:
            continue
        if _is_intermolecular_etherification(step):
            census_vouched += 1
            klass = recognize_reaction_type(step)
            if klass is None or "etherification" not in klass:
                span_demoted += 1
    assert census_vouched > 0
    assert span_demoted > 0     # the span catches bundles the whole-molecule census admits


def test_the_center_is_digest_invisible_and_round_trips_through_replay():
    step = _one("COCCOC", ["CO", "COCCO"])
    twin = ExperimentStep.assembling(step.target, step.reactants, step.products,
                                     reagents=step.reagents, envelope=step.envelope)
    assert step.reaction_center is not None and twin.reaction_center is None
    assert step.digest == twin.digest        # the centre does NOT enter identity (compare=False)
    assert step == twin                       # equality ignores the centre
    replayed = _step_from_payload(_step_to_payload(step))
    assert replayed.reaction_center is not None
    assert recognize_reaction_type(step) == recognize_reaction_type(replayed)   # live == replay
    assert step.digest == replayed.digest


def test_a_centreless_payload_reconstructs_but_now_fails_closed():
    # TAMPER-HARDENING-01: an old / nulled-centre payload must still RECONSTRUCT, but recognition no longer falls
    # back to the whole-molecule census -- a centre-less step is DEMOTED (fail-closed).  This is the polarity that
    # shuts the R59 fiction tamper channel: a serialized replay whose ``reaction_center`` was stripped can only cost
    # a vouch (false-UNRECOGNIZED, safe), never mint one (false-VOUCH).
    step = _one("COC", ["CO", "CO"])
    payload = _step_to_payload(step)
    del payload["reaction_center"]                     # simulate a pre-R58 / tampered replay envelope
    revived = _step_from_payload(payload)
    assert revived.reaction_center is None
    assert recognize_reaction_type(revived) is None    # no census fallback -> demoted


def test_the_hand_built_bundled_fake_is_still_demoted_when_centreless():
    # glycol + DME -> dimethoxyethane + water, hand-built (no span).  It demoted before (R57 clause iii) and demotes
    # now (TAMPER-HARDENING-01 centre-absent fail-closed) -- the outcome is unchanged, only the mechanism.
    water = structure_by_name("water").molecule
    from smartchem.conditions import ConditionEnvelope
    from smartchem.experiment.step import STEP_SCHEMA
    step = ExperimentStep(STEP_SCHEMA, parse_smiles("COCCOC"),
                          (parse_smiles("OCCO"), parse_smiles("COC")), (parse_smiles("COCCOC"), water),
                          (), ConditionEnvelope.unknown())
    assert step.reaction_center is None
    assert recognize_reaction_type(step) is None


def test_escape7_is_still_shut_the_amination_fake_stays_demoted():
    # R60 re-framing: the byte-identical reaction centre is shared by caffeine (real) and the aryl-amination
    # FAKE, so the span alone cannot separate them; R60's census-locked recognizer now vouches caffeine while the
    # FAKE stays demoted -- the real escape-#7 invariant, unchanged by R58's span refit.
    caff = probe.caffeine_now_vouched_fake_demoted()
    assert caff["caffeine_has_vouched_route"] is True
    assert caff["amination_fake_demoted"] is True


def test_the_dimethyl_ether_frontier_carries_a_vouched_route():
    # the full-frontier 0-false-vouch sweep is asserted by test_probe_validates_and_frozen_hash_stable
    # (probe.validate() -> frontier_soundness); this is the fast consumer-level check.
    resp = run_compilation(build_recompile_request("dimethyl ether", max_depth=3))
    fr = resp.affordability_frontier
    assert fr
    # DISPOSITION-01: the fiction rides ``fiction_blockers`` now -- read both channels (else this goes vacuously true).
    assert any(
        not any("unrecognized reaction type" in b
                for b in ((getattr(e.cost_vector, "hard_blockers", ()) or ())
                          + (getattr(e.cost_vector, "fiction_blockers", ()) or ())))
        for e in fr
    )


def test_a_zero_step_route_is_vacuously_vouched():
    assert route_reaction_type_blockers(SimpleNamespace(steps=())) == ()


def test_reaction_center_gate_semantics():
    # ether/ester centre (X=O)
    o = ReactionCenter.of([("C", "O", 1), ("O", "H", 1)], [("O", "C", 1), ("H", "O", 1)], 1)
    assert o.is_elementary_condensation(("O",)) is True
    assert o.is_elementary_condensation() is True
    # amide centre (X=N): acyl family yes, ether no
    n = ReactionCenter.of([("C", "N", 1), ("H", "O", 1)], [("C", "O", 1), ("H", "N", 1)], 1)
    assert n.is_elementary_condensation(("O",)) is False
    assert n.is_elementary_condensation() is True
    # a C-C gluing centre: neither
    cc = ReactionCenter.of([("C", "C", 1), ("H", "O", 1)], [("C", "H", 1), ("C", "O", 1)], 1)
    assert cc.is_elementary_condensation() is False
    # elementary signature but two disjoint components: rejected (connectedness clause)
    two = ReactionCenter.of([("C", "O", 1), ("H", "O", 1)], [("C", "O", 1), ("H", "O", 1)], 2)
    assert two.is_elementary_condensation() is False
    # round-trip
    assert ReactionCenter.from_payload(o.to_payload()) == o
    assert o.schema_version == REACTION_CENTER_SCHEMA
