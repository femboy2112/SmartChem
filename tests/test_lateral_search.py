"""Item 3 -- the bounded lateral-isomerization closure (:mod:`smartchem.lateral_search`), the epic's SOUND core.

The load-bearing pins are the SOUNDNESS ones: (1) the closure TERMINATES on its own visited-set even when the family
graph has an isomerization cycle A<->B (the Cope self-inverse), and reports COMPLETE honestly; (2) the state_budget
truncation is reported as INCOMPLETE (fail-closed, never a false "found everything"); (3) a reconstructed route is a
real chain of guarded lateral edges the oracle vouches; (4) it stays STRICTLY separate from the W1 route search -- a
LateralRewriteEdge's forget() still raises, so a lateral edge can never enter the decompiler/conditions path.
"""
from __future__ import annotations

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.lateral_rewrite import COPE, ELECTRO_6PI, LATERAL_FAMILIES, LateralRewriteError, rewrite_edges
from smartchem.lateral_search import (
    COMPLETE_TO_DEPTH, INCOMPLETE_STATE_BUDGET, lateral_closure, lateral_route_to,
)
from smartchem.smiles import parse_smiles, resonance_identity


def test_closure_of_a_terminal_isomer_is_just_itself():
    rec = lateral_closure(parse_smiles("c1ccccc1"))     # benzene: no guarded lateral rewrite
    assert rec.complete and len(rec.isomers) == 1 and len(rec.edges) == 0


def test_electrocyclization_closure_reaches_the_open_isomer():
    rec = lateral_closure(parse_smiles("C1=CCCC=C1"))    # 1,3-cyclohexadiene -> 1,3,5-hexatriene (6pi)
    assert rec.complete
    ids = {resonance_identity(m) for m in rec.isomers}
    assert resonance_identity(parse_smiles("C=CC=CC=C")) in ids
    assert len(rec.isomers) == 2


def test_cope_cycle_terminates_via_the_visited_set():
    # 3-methyl-1,5-hexadiene Cope-shifts to a distinct isomer that shifts BACK -- an A<->B cycle.  The visited-set
    # (resonance_identity) must dedup B and NOT loop forever; the closure is COMPLETE with exactly two states.
    rec = lateral_closure(parse_smiles("C=CC(C)CC=C"), (COPE,), depth=8)
    assert rec.status == COMPLETE_TO_DEPTH
    assert len(rec.isomers) == 2                          # seed + its one distinct [3,3] isomer, no blow-up


def test_state_budget_truncation_is_reported_incomplete():
    # a tiny state_budget forces truncation on any non-trivial closure; it must fail-closed to INCOMPLETE, never
    # claim COMPLETE.
    rec = lateral_closure(parse_smiles("C1=CCCC=C1"), depth=4, state_budget=1)
    assert rec.status == INCOMPLETE_STATE_BUDGET and not rec.complete


def test_route_reconstruction_is_a_vouched_chain():
    seed = parse_smiles("C1=CCCC=C1")                     # cyclohexadiene
    goal = parse_smiles("C=CC=CC=C")                      # hexatriene
    route = lateral_route_to(seed, goal, depth=4)
    assert route is not None and len(route) == 1
    # every step of the reconstructed route is a guarded lateral edge the oracle recognizes.
    for edge in route:
        step = ExperimentStep.from_transform(edge, envelope=None)
        assert recognize_reaction_type(step) is not None


def test_route_to_unreachable_is_none_not_a_partial_claim():
    seed = parse_smiles("C1=CCCC=C1")
    assert lateral_route_to(seed, parse_smiles("CCCCCC"), depth=4) is None   # different formula, unreachable
    assert lateral_route_to(seed, parse_smiles("C1=CCCC=C1")) == ()          # seed==goal -> empty route


def test_lateral_edges_still_refuse_the_w1_decompiler_path():
    # the SOUNDNESS boundary the whole module rests on: a lateral edge has no strict-descent image, so forget() raises
    # -- so a lateral edge can never be dropped into a search_routes provider/conditions path.  Unchanged by item 3.
    edge = rewrite_edges(ELECTRO_6PI, parse_smiles("C1=CCCC=C1"))[0]
    try:
        edge.forget()
        raise AssertionError("LateralRewriteEdge.forget() must raise the W1 boundary")
    except LateralRewriteError:
        pass


def test_closure_ranges_over_all_lateral_families_by_default():
    # the default family set is every lateral family (sigmatropic + electrocyclic), so the closure is archetype-generic.
    assert len(LATERAL_FAMILIES) == 6
    # a seed reachable only by electrocyclization is still found under the default (all-family) closure.
    rec = lateral_closure(parse_smiles("C1=CCC1"))        # cyclobutene (4pi)
    assert rec.reaches(parse_smiles("C=CC=C"))
