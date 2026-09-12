"""POOR-MAN-OUT-OF-CENTER-RECOGNIZER-DEFER-01 (R52, PR-2): the third verified defer of the ingenuity reward.

The committed probe (:mod:`experiments.poor_man_out_of_center_recognizer_defer_probe`) is the frozen evidence
that the "out-of-centre recognizer" proposed as KILL-1's unlock #2 MOVES the kitchen-boundary collision rather
than closing it (a tertiary carbinol re-collides with a primary one under any functional-group recognizer), and
that it has no live consumer today (redundant with the R48 feasibility guard; the one reachable O-minor-isomer
route is honest UNKNOWN, not a false-VOUCH).  These are the fast regression pins over the SAME live behavior,
kept independent of the probe so a probe refactor cannot silently drop coverage.  If any fires, either the
defer's premise moved or the substrate-reactivity landscape changed.
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.feasibility import _is_intermolecular_acyl_condensation, feasibility_of_step
from smartchem.experiment.selectivity import DEFAULT_SELECTIVITY, SelectivityStatus, selectivity_of_step
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from experiments import poor_man_out_of_center_recognizer_defer_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_kill_the_recognizer_moves_the_collision_it_does_not_close_it():
    # THE load-bearing kill: pentyl acetate (kitchen) and tert-butyl acetate (NOT a Fischer one-pot -- tertiary
    # carbinol, E1 dehydration) share a byte-identical atom-mapped edit AND byte-identical out-of-centre
    # functional groups, so both reach the recognizer's NEUTRAL verdict, yet only pentyl is kitchen.  The
    # separating determinant (carbinol degree 1 vs 3) lives AT the centre and is not a functional group the
    # out-of-centre recognizer can read.
    sc = probe.steric_collision()
    assert sc["edit_signatures_identical_pentyl_tbu"] is True
    assert sc["pentyl_out_of_center_nucleophiles"] == [] == sc["tbu_out_of_center_nucleophiles"]
    assert sc["pentyl_recognizer"] == sc["tbu_recognizer"] == "NEUTRAL"
    assert sc["pentyl_carbinol_degree"] == 1 and sc["tbu_carbinol_degree"] == 3
    assert sc["collision_survives_on_steric_blade"] is True


def test_the_recognizer_does_catch_the_amine_blade_non_vacuity():
    # non-vacuity: it is not a no-op -- it DOES EXCLUDE 5-aminopentyl acetate (a real competing free amine),
    # which is exactly why the surviving tert-butyl collision proves the approach moves the collision, not that
    # the recognizer does nothing.
    alc_amino = parse_smiles("NCCCCCO")
    alc_pentyl = parse_smiles("CCCCCO")
    assert probe.out_of_center_nucleophiles(alc_amino) == ("amine",)
    assert probe.recognizer_verdict(alc_amino) == "EXCLUDE"
    assert probe.recognizer_verdict(alc_pentyl) == "NEUTRAL"


def _fischer_step(alcohol_smiles: str, ester_smiles: str) -> ExperimentStep:
    acid = parse_smiles("CC(=O)O")
    water = structure_by_name("water").molecule
    products = (parse_smiles(ester_smiles), water)
    return ExperimentStep(
        STEP_SCHEMA, target=products[0], reactants=(acid, parse_smiles(alcohol_smiles)),
        products=products, reagents=(), envelope=ConditionEnvelope.unknown(),
    )


def test_redundant_with_the_r48_feasibility_guard():
    # the R48 domain guard already UNKNOWNs BOTH the kitchen and the non-kitchen free-acid Fischer condensation,
    # so a feasibility-layer recognizer would be dead code (no false 'kitchen' pass to remove for the class).
    for alcohol, ester in (("CCCCCO", "CC(=O)OCCCCC"), ("NCCCCCO", "CC(=O)OCCCCCN")):
        step = _fischer_step(alcohol, ester)
        assert _is_intermolecular_acyl_condensation(step) is True
        assert feasibility_of_step(step).direction.value == "UNKNOWN"


def test_o_minor_isomer_route_is_honest_unknown_not_a_false_vouch():
    # the one reachable route to the O-minor-isomer registered target is honest UNKNOWN on BOTH selectivity and
    # feasibility -- loud silence, not a fabricated 'kitchen' pass (R49: silence is not a false-VOUCH), so the
    # recognizer has no live output to change.
    tgt_ns = structure_by_name("4-aminophenyl acetate")
    assert tgt_ns is not None
    tgt = tgt_ns.molecule
    aminophenol = structure_by_name("4-aminophenol").molecule
    water = structure_by_name("water").molecule
    step = ExperimentStep(
        STEP_SCHEMA, target=tgt, reactants=(aminophenol, parse_smiles("CC(=O)O")),
        products=(tgt, water), reagents=(), envelope=ConditionEnvelope.unknown(),
    )
    assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.UNKNOWN
    assert feasibility_of_step(step).direction.value == "UNKNOWN"
