"""OPERATION XIV -- the intramolecular-lactonization RECOGNIZER (25th class) + its wiring into search_event_routes.

This is the adversary-gated acceptance battery for the type-3 event becoming fully live: a generator-independent,
content-deterministic recognizer that VOUCHES a lactonization step, and a bounded coproduct provider wired into
``search_event_routes`` under a rank-INCREASING termination proof.  The load-bearing soundness pins (the task's ten
points):

1. the recognizer is GENERATOR-INDEPENDENT and content-deterministic (it vouches a HAND-BUILT step, re-deriving the
   forward esterification from the molecules, never trusting provenance);
2. the bounded event provider is wired (a lactone target yields a type-3 route);
3. a proper per-route COPRODUCT budget (``max_coproduct_events``; 0 disables, N bounds);
4. the well-founded ``(coproduct_events, atoms, hops)`` measure ADMITS the rank-increasing step and TERMINATES;
5. accurate completeness receipts (COMPLETE with no truncation; fail-closed INCOMPLETE on a budget/hop cut);
6. inverse-cycle refusal (a coproduct event cannot close a cycle; the ancestor guard holds);
7. reagent + coproduct conservation (the ExperimentStep certificate; exactly one water);
8. EXACT structural identity -- a same-formula isomer is refused (no formula-based collapse);
9. CROSS-FAMILY adversarial controls -- retro-DA, diacid->anhydride, intermolecular ester, scission, lateral all
   refused as lactonization (the recognizer is NOT classify_event's shape verdict);
10. an END-TO-END reachable lactone from a declared hydroxy-acid precursor.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.event_search import (
    EventType,
    classify_event,
    search_event_routes,
)
from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.intramolecular_condensation import (
    LACTONIZATION_CLASS,
    retro_lactonization_edges,
)
from smartchem.smiles import parse_smiles

GBL = parse_smiles("O=C1CCCO1")            # gamma-butyrolactone
HYDROXY_ACID = parse_smiles("OCCCC(=O)O")  # 4-hydroxybutanoic acid, its precursor (3 atoms LARGER)
WATER = parse_smiles("O")


def _handbuilt_lactonization(lactone_smiles, precursor_smiles):
    """A lactonization step built WITHOUT the generator (ExperimentStep.assembling from raw multisets) -- so a
    vouch here proves recognition is generator-INDEPENDENT."""
    lactone = parse_smiles(lactone_smiles)
    precursor = parse_smiles(precursor_smiles)
    return ExperimentStep.assembling(lactone, (precursor,), (lactone, parse_smiles("O")), reagents=())


# -- (1) GENERATOR-INDEPENDENT, CONTENT-DETERMINISTIC recognition --------------------------------------------------

def test_recognizer_vouches_a_handbuilt_step_not_from_the_generator():
    step = _handbuilt_lactonization("O=C1CCCO1", "OCCCC(=O)O")
    assert recognize_reaction_type(step) == LACTONIZATION_CLASS   # vouched though never touched by the generator


def test_recognition_is_content_deterministic():
    step = _handbuilt_lactonization("O=C1CCCO1", "OCCCC(=O)O")
    assert recognize_reaction_type(step) == recognize_reaction_type(step) == LACTONIZATION_CLASS


def test_the_registry_entry_names_the_same_class_the_generator_stamps():
    # no string drift: the oracle display name IS the generator's LACTONIZATION_CLASS constant.
    names = {name for name, _pred in _RECOGNIZERS}
    assert LACTONIZATION_CLASS in names


@pytest.mark.parametrize("lactone,precursor", [
    ("O=C1CCO1", "OCCC(=O)O"),             # beta-propiolactone <- 3-hydroxypropanoic acid
    ("O=C1CCCO1", "OCCCC(=O)O"),           # gamma-butyrolactone <- 4-hydroxybutanoic acid
    ("O=C1CCCCO1", "OCCCCC(=O)O"),         # delta-valerolactone <- 5-hydroxypentanoic acid
])
def test_generated_and_handbuilt_lactonizations_agree_as_vouched(lactone, precursor):
    gen_step = ExperimentStep.from_transform(retro_lactonization_edges(parse_smiles(lactone))[0])
    hand_step = _handbuilt_lactonization(lactone, precursor)
    assert recognize_reaction_type(gen_step) == LACTONIZATION_CLASS
    assert recognize_reaction_type(hand_step) == LACTONIZATION_CLASS


# -- (8) EXACT structural identity: conservation is NOT recognition ------------------------------------------------

def test_same_formula_isomer_precursor_is_refused():
    """A C4H8O3 isomer (methyl 3-hydroxypropanoate) balances GBL + water but does NOT lactonize to GBL -- the
    forward re-derivation is the witness, so it is refused.  (No formula-based collapse: identity is structural.)"""
    fake = parse_smiles("COC(=O)CCO")
    assert fake.formula == HYDROXY_ACID.formula    # conservation WOULD pass
    step = ExperimentStep.assembling(GBL, (fake,), (GBL, parse_smiles("O")), reagents=())
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS


def test_polyol_lactone_is_vouched_not_formula_collapsed():
    # a polyol lactone whose hydroxy-acid precursor reaches SEVERAL same-formula lactones under the forward
    # re-derivation: recognition must key on STRUCTURAL identity, not the formula string, so the genuine target is
    # still matched.  Build the step via assembling (generator-independent construction) on the correct precursor.
    target = parse_smiles("O=C1OCC(O)C(O)C1O")
    (edge,) = retro_lactonization_edges(target)
    precursor = edge.products[0]
    step = ExperimentStep.assembling(target, (precursor,), (target, parse_smiles("O")), reagents=())
    assert recognize_reaction_type(step) == LACTONIZATION_CLASS


# -- (9) CROSS-FAMILY adversarial controls: the recognizer is NOT classify_event's shape verdict -------------------

def test_retro_diels_alder_is_shape_type3_but_not_lactonization():
    # cyclohexene -> butadiene + ethylene: classify_event buckets it INTRAMOLECULAR_COPRODUCT by SHAPE, but the
    # coproduct is a hydrocarbon, not water -> the recognizer refuses (recognition goes beyond the shape).
    rda = ExperimentStep.assembling(parse_smiles("C=CC=C"), (parse_smiles("C1=CCCCC1"),),
                                    (parse_smiles("C=CC=C"), parse_smiles("C=C")), reagents=())
    assert classify_event(rda) is EventType.INTRAMOLECULAR_COPRODUCT   # SAME shape as a lactonization
    assert recognize_reaction_type(rda) != LACTONIZATION_CLASS         # but NOT recognized as one


def test_diacid_to_anhydride_shares_shape_and_water_but_is_not_lactonization():
    """THE sharp mutation control: succinic acid -> succinic anhydride + water is rank-increasing, one connected
    precursor, water coproduct -- IDENTICAL on every coarse axis to a lactonization -- yet it is anhydride
    formation, NOT lactonization (a diacid is not a hydroxy acid).  The forward re-derivation refuses it because a
    carboxyl -OH is not read as an alcohol, so the witness is doing load-bearing work, not rubber-stamping shape."""
    step = ExperimentStep.assembling(parse_smiles("O=C1CCC(=O)O1"), (parse_smiles("OC(=O)CCC(=O)O"),),
                                     (parse_smiles("O=C1CCC(=O)O1"), parse_smiles("O")), reagents=())
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT  # same type-3 shape + water coproduct
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS        # refused: no forward lactonization


def test_intermolecular_esterification_is_not_lactonization():
    # 2 reactants: acyl condensation owns it, lactonization (1 connected precursor) does not.
    step = ExperimentStep.assembling(
        parse_smiles("CC(=O)OC"), (parse_smiles("CC(=O)O"), parse_smiles("CO")),
        (parse_smiles("CC(=O)OC"), parse_smiles("O")), reagents=())
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS


def test_a_lateral_isomerization_is_not_lactonization():
    step = ExperimentStep.assembling(parse_smiles("C1=CCCC=C1"), (parse_smiles("C=CC=CC=C"),),
                                     (parse_smiles("C1=CCCC=C1"),), reagents=())
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS   # 1->1 no coproduct: not a lactonization


def test_a_scission_is_not_lactonization():
    step = ExperimentStep.assembling(
        parse_smiles("CC(=O)OC(=O)C"), (parse_smiles("CC(=O)O"), parse_smiles("CC(=O)O")),
        (parse_smiles("CC(=O)OC(=O)C"), parse_smiles("O")), reagents=())
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS


def test_a_charged_target_is_refused_fail_closed():
    # a charge-CONSERVING but charged lactonization (-1 precursor -> -1 lactone + neutral water): the step builds,
    # but the recognizer's is_closed_shell_neutral guard refuses a charged species (out of the neutral domain).
    from smartchem.category import Molecule
    ct = Molecule(GBL.atoms, GBL.bonds, charge=-1)
    cp = Molecule(HYDROXY_ACID.atoms, HYDROXY_ACID.bonds, charge=-1)
    step = ExperimentStep.assembling(ct, (cp,), (ct, parse_smiles("O")), reagents=())   # -1 -> -1 + 0 conserves
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS


# -- (2)(10) the bounded provider is wired + an END-TO-END reachable lactone ---------------------------------------

def test_end_to_end_lactone_reachable_from_a_declared_hydroxy_acid_and_vouched():
    res = search_event_routes(GBL, reagents=(), available=(HYDROXY_ACID,), lateral_hops=0, max_coproduct_events=1)
    assert len(res.routes) == 1
    (route,) = res.routes
    (step,) = route.steps
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT
    assert recognize_reaction_type(step) == LACTONIZATION_CLASS          # the emitted step is oracle-VOUCHED
    assert route.final_target.canonical() == GBL.canonical()
    assert res.receipt.complete                                          # (5) honest COMPLETE receipt
    assert res.event_type_counts()[EventType.INTRAMOLECULAR_COPRODUCT] == 1


# -- (7) reagent + coproduct conservation --------------------------------------------------------------------------

def test_the_type3_step_conserves_and_expels_exactly_one_water():
    res = search_event_routes(GBL, reagents=(), available=(HYDROXY_ACID,), lateral_hops=0, max_coproduct_events=1)
    (step,) = res.routes[0].steps
    assert step.schema_version          # built without raising -> conservation re-checked by the step certificate
    from smartchem.category import Config
    assert Config.of(*step.byproducts) == Config.of(WATER)   # exactly one water coproduct


# -- (3) the per-route COPRODUCT budget ----------------------------------------------------------------------------

def test_max_coproduct_events_zero_disables_the_producer():
    off = search_event_routes(GBL, reagents=(), available=(HYDROXY_ACID,), lateral_hops=0, max_coproduct_events=0)
    assert len(off.routes) == 0
    assert off.receipt.coproduct_events_considered == 0


def test_negative_max_coproduct_events_is_refused():
    with pytest.raises(ValueError):
        search_event_routes(GBL, reagents=(), available=(HYDROXY_ACID,), max_coproduct_events=-1)


# -- (4)(6) rank-increasing admission + TERMINATION + no inverse cycle ----------------------------------------------

def test_the_returned_coproduct_step_is_rank_increasing():
    res = search_event_routes(GBL, reagents=(), available=(HYDROXY_ACID,), lateral_hops=0, max_coproduct_events=1)
    (step,) = res.routes[0].steps
    # the precursor is strictly LARGER than the target -- the step the pure (atoms, hops) measure could NOT admit.
    assert len(step.reactants[0].atoms) > len(step.target.atoms)


def test_search_terminates_under_a_hostile_coproduct_budget_with_no_stock():
    # generous coproduct + lateral + depth budgets, NO stock: termination is guaranteed by the lexicographic triple
    # (cop_left strictly decreases on every type-3 edge), so this must halt with no frontier blow-up.
    res = search_event_routes(GBL, reagents=(), available=(), lateral_hops=3, max_coproduct_events=4, max_depth=6)
    assert len(res.routes) == 0           # nothing is on hand, so nothing terminates a branch
    assert res.receipt.nodes_visited <= 8  # bounded: the hydroxy-acid precursor + its handful of scission children


def test_a_coproduct_event_cannot_close_an_inverse_cycle():
    # even with a lavish coproduct budget, the strictly-decreasing cop_left (and the ancestor guard) forbid a cycle
    # back to the target; with no stock there is simply no completed route, and the search terminates.
    res = search_event_routes(GBL, reagents=(), available=(), lateral_hops=0, max_coproduct_events=5, max_depth=8)
    assert len(res.routes) == 0


# -- (5) completeness-receipt honesty ------------------------------------------------------------------------------

def test_coproduct_match_budget_truncation_is_reported_incomplete():
    # glycolide has TWO in-ring ester sites; a coproduct_match_budget of 1 scans only one -> the enumeration is
    # non-exhaustive, which the receipt must report as INCOMPLETE (fail-closed), never masquerade as complete.
    glycolide = parse_smiles("O=C1OCC(=O)OC1")
    res = search_event_routes(glycolide, reagents=(), available=(), lateral_hops=0, max_coproduct_events=1,
                              coproduct_match_budget=1, max_depth=2)
    assert res.receipt.coproduct_match_truncated >= 1
    assert not res.receipt.complete
