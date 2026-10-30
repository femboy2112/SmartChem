"""Bounded typed-event route search (#104 / #123 / #125) -- proof obligations + the control battery.

The load-bearing SOUNDNESS pins (the #125 acceptance clauses + the plan's required controls):

* TERMINATION on the separate well-founded measure: every returned route is monotone under the lexicographic
  ``(atom_count, hops_left)`` order (a scission precursor is strictly smaller; a lateral precursor is the same
  size) and never uses more than ``lateral_hops`` CONNECTED_LATERAL steps;
* the FORCING CONSUMER: a [3,3]/electrocyclic target UNREACHABLE by ``search_routes`` becomes reachable by one
  lateral hop, and the oracle vouches the hop;
* SCISSION PARITY / replay integrity: ``lateral_hops=0`` reproduces EXACTLY the ``search_routes`` route set;
* INVERSE PAIRS / rank-flat cycles TERMINATE (the A->B->A inverse is cut by the ancestor guard, not looped);
* IDENTITY-ONLY fake rewrites and NONCONSERVING steps are refused; BUDGET exhaustion reports honest INCOMPLETE;
* the TYPED-EVENT TAXONOMY is complete and fail-closed (scission / connected-lateral / intramolecular-coproduct),
  the third being the DEFINED-but-DEFERRED category (no generator emits it here);
* the forget()-FREE boundary holds: a lateral edge still refuses the W1 decompiler path.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.event_search import (
    EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA,
    EventClassificationError,
    EventType,
    classify_event,
    search_event_routes,
)
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep, StepError
from smartchem.lateral_rewrite import ELECTRO_6PI, LateralRewriteError, rewrite_edges
from smartchem.smiles import parse_smiles

RING = parse_smiles("C1=CCCC=C1")       # 1,3-cyclohexadiene
OPEN = parse_smiles("C=CC=CC=C")        # 1,3,5-hexatriene (its rank-flat open isomer)
COPE = parse_smiles("C=CC(C)CC=C")      # 3-methyl-1,5-hexadiene (a Cope self-inverse A<->B)
BENZENE = parse_smiles("c1ccccc1")      # no guarded lateral rewrite (an identity-only would be the only match)

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
PARA_KW = dict(
    reagents=(parse_smiles("O"), parse_smiles("CC(=O)O"), parse_smiles("CC(=O)OC(=O)C")),
    available=(AMP,),
    max_depth=1,
)


def _is_monotone_and_hop_bounded(route, hops: int) -> bool:
    """Every step obeys the lexicographic measure and the route uses <= ``hops`` lateral steps (the executable
    content of the termination proof)."""
    laterals = 0
    for step in route.steps:
        et = classify_event(step)
        if et is EventType.SCISSION:
            if not all(len(p.atoms) < len(step.target.atoms) for p in step.reactants):
                return False                       # a scission precursor must be strictly smaller (W1)
        elif et is EventType.CONNECTED_LATERAL:
            laterals += 1
            if len(step.reactants[0].atoms) != len(step.target.atoms):
                return False                       # a lateral precursor must be the SAME atom count (rank-flat)
    return laterals <= hops


# -- (1) FORCING CONSUMER: a lateral-only reach search_routes is blind to -------------------------------------------

def test_forcing_consumer_lateral_reachable_only_through_the_event_search():
    # search_routes cannot reach the ring from its open isomer -- that step is rank-flat, no W1 scission.
    assert len(search_routes(RING, reagents=(), available=(OPEN,)).routes) == 0
    result = search_event_routes(RING, reagents=(), available=(OPEN,), lateral_hops=1)
    assert len(result.routes) == 1
    assert result.receipt.complete
    counts = result.event_type_counts()
    assert counts[EventType.CONNECTED_LATERAL] == 1 and counts[EventType.SCISSION] == 0


def test_the_lateral_hop_is_oracle_vouched():
    result = search_event_routes(RING, reagents=(), available=(OPEN,), lateral_hops=1)
    (route,) = result.routes
    (step,) = route.steps
    assert classify_event(step) is EventType.CONNECTED_LATERAL
    assert recognize_reaction_type(step) is not None          # a real reaction TYPE, not demoted-unrecognized
    assert route.final_target.canonical() == RING.canonical()


# -- (2) TERMINATION on the separate well-founded measure -----------------------------------------------------------

def test_every_returned_route_is_measure_monotone_and_hop_bounded():
    er = search_event_routes(RING, reagents=(), available=(OPEN,), lateral_hops=1)
    assert all(_is_monotone_and_hop_bounded(r, 1) for r in er.routes)
    pe = search_event_routes(PARA, lateral_hops=1, **PARA_KW)
    assert pe.routes and all(_is_monotone_and_hop_bounded(r, 1) for r in pe.routes)


def test_inverse_pair_rank_flat_cycle_terminates_with_no_route():
    # a Cope self-inverse target with NO stock: the A->B->A inverse must be CUT (ancestor guard), not looped.
    # Generous hop + depth budgets; termination is guaranteed by the lexicographic measure regardless.
    er = search_event_routes(COPE, reagents=(), available=(), lateral_hops=5, max_depth=6)
    assert len(er.routes) == 0
    assert er.receipt.nodes_visited <= 4          # seed + its one distinct isomer; no frontier blow-up


def test_ancestor_that_is_genuine_stock_terminates_a_real_route():
    # the SAME inverse geometry, but now the isomer IS on hand -> a genuine 1-hop route exists and terminates.
    (iso_edge,) = [e for e in rewrite_edges(ELECTRO_6PI, RING)]  # ring -> open; so open makes ring (the precursor)
    iso = iso_edge.products[0]
    er = search_event_routes(RING, reagents=(), available=(iso,), lateral_hops=1)
    assert len(er.routes) == 1


# -- (3) SCISSION PARITY / replay integrity -------------------------------------------------------------------------

def test_lateral_hops_zero_reproduces_the_search_routes_route_set():
    sr = {r.digest for r in search_routes(PARA, **PARA_KW).routes}
    e0 = {r.digest for r in search_event_routes(PARA, lateral_hops=0, **PARA_KW).routes}
    assert e0 == sr and len(sr) >= 1
    e1 = {r.digest for r in search_event_routes(PARA, lateral_hops=1, **PARA_KW).routes}
    assert sr <= e1                                # enabling laterals never DROPS a scission route


def test_the_event_search_uses_its_own_opt_in_receipt_schema():
    # the frozen RouteSearchReceipt schema is untouched: this is a separate opt-in surface.
    er = search_event_routes(RING, reagents=(), available=(OPEN,), lateral_hops=1)
    assert er.receipt.schema_version == EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA


# -- (4) IDENTITY-ONLY fakes, NONCONSERVING steps, and the forget()-free boundary -----------------------------------

def test_identity_only_rewrite_yields_no_lateral_event():
    # benzene admits no non-degenerate guarded lateral rewrite (a self-map is dropped), so no lateral event appears
    # even with hops available: the search finds nothing (no scission to stock either) and says so honestly.
    er = search_event_routes(BENZENE, reagents=(), available=(), lateral_hops=2)
    assert len(er.routes) == 0
    assert er.event_type_counts()[EventType.CONNECTED_LATERAL] == 0


def test_a_nonconserving_step_cannot_be_built_so_cannot_enter_a_route():
    # the ExperimentStep conservation certificate refuses a non-balancing event at construction -- a nonconserving
    # coproduct can never become a vouched search event.
    with pytest.raises(StepError):
        ExperimentStep.assembling(RING, (OPEN,), (RING, parse_smiles("O")), reagents=())  # extra water: unbalanced


def test_lateral_edges_still_refuse_the_w1_decompiler_path():
    edge = rewrite_edges(ELECTRO_6PI, RING)[0]
    with pytest.raises(LateralRewriteError):
        edge.forget()                              # the boundary the whole opt-in search rests on is unchanged


# -- (5) BUDGET exhaustion -> honest INCOMPLETE ---------------------------------------------------------------------

def test_starved_lateral_match_budget_is_reported_incomplete():
    er = search_event_routes(RING, reagents=(), available=(), lateral_hops=1, lateral_match_budget=1, max_depth=2)
    assert not er.receipt.complete                 # fail-closed: a truncated search never claims it found everything


def test_lateral_hops_boundary_truncation_is_reported_incomplete():
    # a reachable-only-past-the-budget lateral target: with hops=1 but the reach needing 2 hops, the hop boundary
    # is hit and the receipt is INCOMPLETE (the lateral analogue of depth truncation).  COPE reaches its isomer in
    # one hop then wants another (back, refused) -- but a node beyond the spent budget flags the truncation.
    er = search_event_routes(COPE, reagents=(), available=(), lateral_hops=1, max_depth=4)
    assert not er.receipt.complete


# -- (6) the TYPED-EVENT TAXONOMY: complete, fail-closed, and the DEFERRED third class -------------------------------

def test_classify_event_covers_all_three_typed_shapes():
    scission = ExperimentStep.assembling(
        parse_smiles("CC(=O)OC(=O)C"), (parse_smiles("CC(=O)O"), parse_smiles("CC(=O)O")),
        (parse_smiles("CC(=O)OC(=O)C"), parse_smiles("O")), reagents=())
    lateral = ExperimentStep.assembling(RING, (OPEN,), (RING,), reagents=())
    intramolecular = ExperimentStep.assembling(      # lactonization expelling water -- the DEFERRED category
        parse_smiles("O=C1CCCO1"), (parse_smiles("OCCCC(=O)O"),),
        (parse_smiles("O=C1CCCO1"), parse_smiles("O")), reagents=())
    assert classify_event(scission) is EventType.SCISSION
    assert classify_event(lateral) is EventType.CONNECTED_LATERAL
    assert classify_event(intramolecular) is EventType.INTRAMOLECULAR_COPRODUCT


def test_the_deferred_intramolecular_coproduct_class_has_no_producer_in_the_search():
    # the category is DEFINED (classifier recognizes its shape) but the shipped search never YIELDS one: no
    # generator emits a connected-1->1-with-coproduct event (CappedScission's >=2-component contract #125 forbids
    # it; no lateral family expels a coproduct).  Over the whole paracetamol route set, zero type-3 events appear.
    pe = search_event_routes(PARA, lateral_hops=1, **PARA_KW)
    assert pe.event_type_counts()[EventType.INTRAMOLECULAR_COPRODUCT] == 0


def test_classify_event_is_fail_closed_on_a_non_step():
    with pytest.raises(EventClassificationError):
        classify_event("not a step")


# -- (7) input validation -------------------------------------------------------------------------------------------

def test_negative_lateral_hops_is_refused():
    with pytest.raises(ValueError):
        search_event_routes(RING, reagents=(), available=(OPEN,), lateral_hops=-1)


def test_a_target_already_on_hand_is_an_immediate_measured_zero():
    er = search_event_routes(RING, reagents=(), available=(RING,), lateral_hops=1)
    assert er.searched_target_on_hand and len(er.routes) == 0 and er.receipt.nodes_visited == 0
