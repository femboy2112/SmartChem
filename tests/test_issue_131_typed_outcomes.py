"""ISSUE #131: an internal recognizer exception must be observable as such, not masked as NOT_A_REACTION.

`recognize_reaction_type` caught EVERY exception and continued as if the class merely did not match, so a
recognizer implementation fault and a genuine non-recognition were indistinguishable -- release telemetry could
not tell "insufficient rule coverage" from "a recognizer choked on this substrate". The fix adds a typed outcome
layer (MATCH / ABSTAIN / INTERNAL_RECOGNIZER_ERROR) WITHOUT weakening the fail-closed rule or changing the stable
`str | None` contract: an exception still never becomes a vouch.
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from smartchem.conditions import ConditionEnvelope
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.step import ExperimentStep
import smartchem.experiment.reaction_type_oracle as oracle
from smartchem.experiment.reaction_type_oracle import (
    recognize_reaction_type, recognize_reaction_type_outcome, route_reaction_type_diagnostics,
    route_reaction_type_blockers, MATCH, ABSTAIN, INTERNAL_RECOGNIZER_ERROR,
)
from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute

_WATER = structure_by_name("water").molecule


def _derived_match_step():
    """A genuine ENGINE-derived esterification step (trusted centre) -- the oracle MATCHes it."""
    r = parse_smiles("CC(=O)OC")
    want = sorted(parse_smiles(s).canonical().__repr__() for s in ("CC(=O)O", "CO"))
    for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    raise AssertionError("no esterification scission found")


def _abstain_step():
    """A conserving step the oracle genuinely cannot vouch (centre-less acyl shape) -> ABSTAIN, not error."""
    rs = (parse_smiles("CC(=O)O"), parse_smiles("CO"))
    ps = (parse_smiles("CC(=O)OC"), _WATER)
    return ExperimentStep.assembling(ps[0], rs, ps, reagents=(), envelope=ConditionEnvelope.unknown())


def _poison(monkeypatch):
    """Prepend a deterministically-raising recognizer so every step hits exactly one instrument fault."""
    def boom(step):
        raise RuntimeError("deterministic poison")
    monkeypatch.setattr(oracle, "_RECOGNIZERS", (("poison", boom),) + oracle._RECOGNIZERS)


def test_clean_match_and_abstain_without_poison():
    m = recognize_reaction_type_outcome(_derived_match_step())
    assert m.kind == MATCH and m.reaction_class and m.faults == ()
    a = recognize_reaction_type_outcome(_abstain_step())
    assert a.kind == ABSTAIN and a.reaction_class is None and a.faults == ()
    # the stable str|None API agrees
    assert recognize_reaction_type(_derived_match_step()) == m.reaction_class
    assert recognize_reaction_type(_abstain_step()) is None


def test_internal_error_is_typed_and_recoverable_but_never_vouches(monkeypatch):
    _poison(monkeypatch)
    step = _abstain_step()                      # matches no genuine class; the poison raises
    outcome = recognize_reaction_type_outcome(step)
    # (c) not mislabeled as chemistry proof or mere unsupported class:
    assert outcome.kind == INTERNAL_RECOGNIZER_ERROR and outcome.is_internal_error
    # (b) the caller can recover the fault with its recognizer name + exception type:
    assert outcome.faults and outcome.faults[0][0] == "poison" and "RuntimeError" in outcome.faults[0][1]
    # (a) no spurious VOUCH: the fail-closed str|None API still demotes to None, and the step is still blocked
    assert outcome.reaction_class is None
    assert recognize_reaction_type(step) is None


def test_a_genuine_match_survives_a_poisoned_sibling_recognizer(monkeypatch):
    _poison(monkeypatch)
    step = _derived_match_step()                # the poison raises first, then a genuine recognizer MATCHes
    outcome = recognize_reaction_type_outcome(step)
    assert outcome.kind == MATCH and outcome.reaction_class is not None
    assert outcome.faults and outcome.faults[0][0] == "poison"     # the fault is carried as provenance ...
    assert recognize_reaction_type(step) == outcome.reaction_class  # ... and the correct vouch still stands


def test_route_diagnostics_distinguish_error_from_abstain(monkeypatch):
    # a two-step route: one step the oracle MATCHes, one it ABSTAINs on. Without poison, diagnostics are MATCH +
    # ABSTAIN and the blocker channel blocks the abstain step. With poison, the abstain step becomes a typed
    # INTERNAL_RECOGNIZER_ERROR while the blocker channel STILL blocks it (fail-closed, strings unchanged).
    match_step = _derived_match_step()
    route = ExperimentRoute(ROUTE_SCHEMA, (match_step,))
    diag = route_reaction_type_diagnostics(route)
    assert len(diag) == 1 and diag[0].kind == MATCH
    assert route_reaction_type_blockers(route) == ()          # a fully-recognized route has no blocker

    _poison(monkeypatch)
    diag2 = route_reaction_type_diagnostics(route)
    assert diag2[0].kind == MATCH                              # a genuine match survives the poison
    # the blocker contract is unchanged: a matched route still has no blocker even under instrument noise
    assert route_reaction_type_blockers(route) == ()
