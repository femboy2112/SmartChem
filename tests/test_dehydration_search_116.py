"""#116 -- alcohol dehydration through the PUBLIC ``search_event_routes`` API (opt-in type-3 producer).

Pins: opting in finds the route and the oracle vouches the step; the DEFAULT grammar is byte-identical to the
released 1.6.0 grammar (digest values measured on the untouched code); no stock means no route with an honest
COMPLETE receipt; the coproduct budget bounds and terminates the search; budget truncation is reported INCOMPLETE; a
genuine two-step route from stock composes a scission with the dehydration (in both orders); and every dehydration
step a route carries re-verifies from its molecules alone, through the oracle AND the independent witness.
"""
from __future__ import annotations

import pytest

from smartchem.elimination import DEHYDRATION_CLASS
from smartchem.elimination_witness import witnesses_dehydration
from smartchem.experiment.activator_ledger import route_activator_blockers
from smartchem.elimination import DehydrationEnumeration, retro_dehydration_enumeration
from smartchem.experiment.event_search import (
    DEFAULT_COPRODUCT_PRODUCERS,
    DEHYDRATION_PRODUCER,
    LACTONIZATION_PRODUCER,
    CoproductProducer,
    EventType,
    UnknownCoproductProducerError,
    classify_event,
    search_event_routes,
)
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles, resonance_identity

P = parse_smiles
WITH_DEHYDRATION = (LACTONIZATION_PRODUCER, DEHYDRATION_PRODUCER)
CYCLOHEXENE = P("C1=CCCCC1")
CYCLOHEXANOL = P("OC1CCCCC1")
WATER = P("O")

#: Measured on the untouched released code (main 11d05bb / v1.6.0, smartchem/ unchanged through 284eac7) BEFORE
#: this change, and re-measured identical after it: the default type-3 grammar must not move.
DEFAULT_GRAMMAR_DIGEST = "d9f572035fe91f54e7e5b71947313a8803db8b3567ee846c33731645d6be2e35"
DEFAULT_CYCLOHEXENE_RECEIPT_DIGEST = "8b66cc9b7f7e8bf2b200b66117739482a14f19bbba1421d231435df33ba182b3"
DEFAULT_CYCLOHEXENE_RESULT_DIGEST = "835930ea6210db0ef49224018271d04798062bde93ec1e25f0e7346eeaf9d174"
DEFAULT_GBL_RESULT_DIGEST = "db5785e2704ef6e8257a5f11559d711ee27fbd35a208932b7916fce05ddf421f"


def _dehydration_steps(result):
    return [s for r in result.routes for s in r.steps if recognize_reaction_type(s) == DEHYDRATION_CLASS]


# -- opt-in finds it; default does not, byte-identically ------------------------------------------------------------

def test_opt_in_finds_cyclohexene_from_cyclohexanol_and_the_step_is_vouched():
    res = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                              coproduct_producers=WITH_DEHYDRATION)
    assert len(res.routes) == 1 and res.receipt.complete
    (step,) = res.routes[0].steps
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT
    assert recognize_reaction_type(step) == DEHYDRATION_CLASS
    assert res.event_type_counts()[EventType.INTRAMOLECULAR_COPRODUCT] == 1


def test_default_grammar_finds_nothing_and_is_byte_identical_to_1_6_0():
    res = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,))
    assert res.routes == () and res.receipt.complete
    assert res.receipt.transform_grammar_digest == DEFAULT_GRAMMAR_DIGEST
    assert res.receipt.digest == DEFAULT_CYCLOHEXENE_RECEIPT_DIGEST
    assert res.digest == DEFAULT_CYCLOHEXENE_RESULT_DIGEST
    explicit = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                                   coproduct_producers=DEFAULT_COPRODUCT_PRODUCERS)
    assert explicit.digest == DEFAULT_CYCLOHEXENE_RESULT_DIGEST


def test_default_lactonization_result_is_byte_identical_to_1_6_0():
    res = search_event_routes(P("O=C1CCCO1"), reagents=(), available=(P("OCCCC(=O)O"),))
    assert len(res.routes) == 1 and res.digest == DEFAULT_GBL_RESULT_DIGEST


def test_a_non_default_producer_set_moves_the_grammar_digest():
    on = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                             coproduct_producers=WITH_DEHYDRATION)
    only = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                               coproduct_producers=(DEHYDRATION_PRODUCER,))
    digests = {DEFAULT_GRAMMAR_DIGEST, on.receipt.transform_grammar_digest, only.receipt.transform_grammar_digest}
    assert len(digests) == 3


def test_max_coproduct_events_zero_disables_the_dehydration_producer_too():
    res = search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                              coproduct_producers=WITH_DEHYDRATION, max_coproduct_events=0)
    assert res.routes == () and res.receipt.coproduct_events_considered == 0


def test_producer_argument_is_validated():
    with pytest.raises(TypeError):
        search_event_routes(CYCLOHEXENE, reagents=(), coproduct_producers=[DEHYDRATION_PRODUCER])
    with pytest.raises(ValueError):
        search_event_routes(CYCLOHEXENE, reagents=(), coproduct_producers=(DEHYDRATION_PRODUCER, DEHYDRATION_PRODUCER))


def _nothing(target, *, budget):
    return DehydrationEnumeration((), True, 0, 0, budget)


@pytest.mark.parametrize("fake", [
    CoproductProducer("dehydration-v1", _nothing),                         # genuine id, enumerates nothing
    CoproductProducer("dehydration-v1", retro_dehydration_enumeration),    # an equal-valued look-alike, not the object
    CoproductProducer("my-producer", retro_dehydration_enumeration),
], ids=["same-id-empty", "equal-lookalike", "new-id"])
def test_the_producer_set_is_closed_and_matched_by_identity(fake):
    with pytest.raises(UnknownCoproductProducerError):
        search_event_routes(CYCLOHEXENE, reagents=(), available=(CYCLOHEXANOL,),
                            coproduct_producers=(LACTONIZATION_PRODUCER, fake))


#: a target both producers can make: alpha-ethylidene-gamma-butyrolactone -- lactonization of
#: 4-hydroxy-2-ethylidenebutanoic acid, or dehydration of alpha-(1-hydroxyethyl)-gamma-butyrolactone (the standard
#: aldol-then-dehydrate route to alpha-alkylidene lactones; the lactone is the beta acyl group (M) admits).  (r5: the
#: former remote-lactone target left the class -- (M) refuses any heteroatom that is not the leaving O / beta acyl.)
_ORDER_TARGET = P("CC=C1CCOC1=O")
_ORDER_STOCK = (P("OCCC(=CC)C(=O)O"), P("CC(O)C1CCOC1=O"))


@pytest.mark.parametrize("max_routes", [100, 1])
def test_caller_producer_order_cannot_change_routes_or_digests(max_routes):
    ld = search_event_routes(_ORDER_TARGET, reagents=(), available=_ORDER_STOCK, max_routes=max_routes,
                             coproduct_producers=(LACTONIZATION_PRODUCER, DEHYDRATION_PRODUCER))
    dl = search_event_routes(_ORDER_TARGET, reagents=(), available=_ORDER_STOCK, max_routes=max_routes,
                             coproduct_producers=(DEHYDRATION_PRODUCER, LACTONIZATION_PRODUCER))
    assert ld.digest == dl.digest
    assert ld.receipt.digest == dl.receipt.digest
    assert [r.digest for r in ld.routes] == [r.digest for r in dl.routes]
    assert len(ld.routes) == (2 if max_routes == 100 else 1)
    if max_routes == 100:
        classes = sorted(recognize_reaction_type(r.steps[0]) for r in ld.routes)
        assert classes.count(DEHYDRATION_CLASS) == 1 and len(set(classes)) == 2      # both producers contribute


# -- no stock, cycles, budgets ---------------------------------------------------------------------------------------

def test_no_stock_means_no_route_with_an_honest_complete_receipt():
    res = search_event_routes(CYCLOHEXENE, reagents=(), available=(), coproduct_producers=WITH_DEHYDRATION)
    assert res.routes == ()
    assert res.receipt.complete                         # every branch exhausted: the empty set is a measurement


@pytest.mark.parametrize("target,reagents", [("C=CC=C", ()), ("C1=CCCCC1", ("O",))])
def test_a_generous_coproduct_budget_cannot_manufacture_stock_and_terminates(target, reagents):
    # with water as a scission reagent too, no alkene <-> alcohol cycle can supply its own feed: cop_left only falls,
    # the ancestor guard refuses a self-referential precursor, and the search ends with nothing.
    res = search_event_routes(P(target), reagents=tuple(P(r) for r in reagents), available=(),
                              coproduct_producers=WITH_DEHYDRATION, max_coproduct_events=5, max_depth=8)
    assert res.routes == () and res.receipt.complete
    assert res.receipt.nodes_visited <= 7


def test_coproduct_match_budget_truncation_is_reported_incomplete():
    # butadiene has two C=C sites; a budget of one examines only the first.
    res = search_event_routes(P("C=CC=C"), reagents=(), coproduct_producers=WITH_DEHYDRATION,
                              coproduct_match_budget=1)
    assert res.receipt.coproduct_match_truncated >= 1 and not res.receipt.complete


def test_a_spent_coproduct_budget_with_a_live_successor_is_reported_incomplete():
    # alpha-ethylidene-gamma-butyrolactone: one dehydration below it is the hydroxyethyl lactone, which still has a live
    # LACTONIZATION successor (the open hydroxy acid) -- but cop_left is 0 there.  (r5: a dehydration can no longer
    # chain into a second dehydration down one lineage -- that precursor would be a diol, which (M) refuses -- so the
    # spent budget is exercised through the mixed producer set.)
    res = search_event_routes(_ORDER_TARGET, reagents=(), coproduct_producers=WITH_DEHYDRATION,
                              max_coproduct_events=1, max_depth=2)
    assert res.receipt.coproduct_events_truncated >= 1 and not res.receipt.complete
    deeper = search_event_routes(_ORDER_TARGET, reagents=(), coproduct_producers=WITH_DEHYDRATION,
                                 max_coproduct_events=2, max_depth=4)
    assert deeper.receipt.coproduct_events_truncated == 0 and deeper.receipt.complete


def test_dehydration_cannot_chain_down_one_lineage():
    """(M) consequence, pinned: from butadiene, but-3-en-2-ol is one dehydration below, and nothing is a second
    dehydration below it (that would be a butanediol).  A generous coproduct budget therefore truncates nothing."""
    res = search_event_routes(P("C=CC=C"), reagents=(), coproduct_producers=WITH_DEHYDRATION,
                              max_coproduct_events=1)
    assert res.receipt.coproduct_events_truncated == 0 and res.receipt.complete


# -- a genuine multi-step route from stock, and replay ---------------------------------------------------------------

@pytest.fixture(scope="module")
def ethyl_crotonate_search():
    """ethyl crotonate from stock 3-hydroxybutanoic acid + ethanol (water as the scission reagent), dehydration opted
    in.  Both orders are real chemistry: dehydrate the beta-hydroxy acid to crotonic acid then Fischer-esterify, or
    esterify first and dehydrate the beta-hydroxy ester.  (r5: the former butane-1,4-diol demo was a false VOUCH --
    under acid BDO cyclodehydrates to THF; (M) now refuses a second hydroxyl anywhere.)"""
    return search_event_routes(CROTONATE, reagents=(WATER,), available=CROTONATE_STOCK,
                               coproduct_producers=WITH_DEHYDRATION, max_depth=4)


CROTONATE = P("CCOC(=O)C=CC")
CROTONATE_STOCK = (P("CC(O)CC(=O)O"), P("CCO"))


def test_a_two_step_route_from_stock_composes_scission_and_dehydration(ethyl_crotonate_search):
    res = ethyl_crotonate_search
    assert res.receipt.complete and len(res.routes) == 2
    stock = {resonance_identity(m) for m in (*CROTONATE_STOCK, WATER)}
    orders = set()
    for route in res.routes:
        assert len(route.steps) == 2
        kinds = tuple(classify_event(s) for s in route.steps)
        assert set(kinds) == {EventType.SCISSION, EventType.INTRAMOLECULAR_COPRODUCT}
        orders.add(kinds)
        classes = {recognize_reaction_type(s) for s in route.steps}
        assert classes == {DEHYDRATION_CLASS, "acyl condensation (esterification/amidation)"}
        assert {resonance_identity(m) for m in route.leaf_inputs} <= stock
    # both orders compose: dehydrate-then-esterify (via crotonic acid) and esterify-then-dehydrate
    assert len(orders) == 2


def test_the_default_grammar_cannot_reach_ethyl_crotonate_from_the_same_stock():
    res = search_event_routes(CROTONATE, reagents=(WATER,), available=CROTONATE_STOCK, max_depth=4)
    assert res.routes == () and res.receipt.complete


def test_a_diol_stock_no_longer_reaches_the_former_demo_target():
    """r5 regression pin: butane-1,4-diol + acetic acid -> but-3-enyl acetate was vouched through but-3-en-1-ol, which
    acid does not make from BDO (it cyclises to THF).  (M) refuses the second hydroxyl, so no route exists."""
    res = search_event_routes(P("C=CCCOC(C)=O"), reagents=(WATER,), available=(P("OCCCCO"), P("CC(=O)O")),
                              coproduct_producers=WITH_DEHYDRATION, max_depth=3)
    assert res.routes == () and res.receipt.complete


def test_every_searched_dehydration_step_replays_from_its_molecules_alone(ethyl_crotonate_search):
    steps = _dehydration_steps(ethyl_crotonate_search)
    assert len(steps) == 2
    for step in steps:
        # rebuild from raw multisets -- no generator, no edge object, no carried centre
        replay = ExperimentStep.assembling(step.target, tuple(step.reactants), tuple(step.products))
        assert recognize_reaction_type(replay) == DEHYDRATION_CLASS
        (precursor,) = replay.reactants
        assert witnesses_dehydration(precursor, replay.target).is_dehydration


def test_a_searched_dehydration_route_is_activator_demoted_until_an_acid_is_declared(ethyl_crotonate_search):
    for route in ethyl_crotonate_search.routes:
        reasons = route_activator_blockers(route)
        assert any("acid dehydration catalyst" in r for r in reasons)
