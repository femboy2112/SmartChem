"""POOR-MAN-DISPOSITION-CHANNEL-01 (R59): a DISTINCT disposition channel un-flattens the two blocker KINDS.

The committed probe (:mod:`experiments.poor_man_disposition_channel_probe`) is the frozen evidence that splitting a
route's hard blockers into two DISJOINT channels -- ``hard_blockers`` (REAL-BUT-HARD) and ``fiction_blockers``
(NOT-A-REACTION, Problem A) -- driving a 3-tier :class:`~smartchem.experiment.affordability.Disposition`, (a) is a
sound strict partial order, (b) keeps the two KINDS disjoint on the wire with the fiction classification served +
serialized distinctly, (c) is HONESTLY data-dark as a RANKING mechanism in production today (0 reachable
REAL_BUT_HARD routes -> verdict-neutral, correct-ahead-of-data) yet proven correct WHEN reachable, and (d) regresses
nothing (fictions stay demoted; the disposition round-trips through replay; prior probes stay frozen).

These are the fast regression pins over the SAME live behaviour, independent of the probe.  The "data-dark" pin is
an ASSERTION, not a footnote: if a real-but-hard route ever becomes reachable it FLIPS and R59 must be re-stated
(a genuine ranking consumer has appeared).  If the "disjoint" pin stops firing, a fiction leaked back into the
real-but-hard channel (the flattening returned).  If the "correct-when-reachable" pin stops firing, the 3-tier
mechanism is wrong.
"""
from __future__ import annotations

from smartchem.experiment.affordability import (
    CostVector, Disposition, dominates, pareto_frontier,
)
from smartchem.service import (
    build_recompile_request, run_compilation, affordability_entry_to_payload, affordability_entry_from_payload,
)
import experiments.poor_man_disposition_channel_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_disposition_is_the_worst_tier_over_the_two_disjoint_channels():
    assert CostVector().disposition is Disposition.CLEAN
    assert CostVector(hard_blockers=("needs Pd",)).disposition is Disposition.REAL_BUT_HARD
    assert CostVector(fiction_blockers=("unrecognized reaction type",)).disposition is Disposition.NOT_A_REACTION
    both = CostVector(hard_blockers=("needs Pd",), fiction_blockers=("unrecognized reaction type",))
    assert both.disposition is Disposition.NOT_A_REACTION   # a fiction voids the whole route


def test_real_but_hard_strictly_outranks_a_cheaper_not_a_reaction():
    # THE un-flattening: a genuine reaction needing an unobtainable catalyst beats a formula-balanced non-reaction
    # even when the fiction is 1000x cheaper -- the partial order the shared hard_blockers tuple used to lose.
    rbh = CostVector(cash=1000.0, hard_blockers=("catalyst not kitchen-obtainable: Pd [industrial]",))
    fic = CostVector(cash=1.0, fiction_blockers=("unrecognized reaction type: no attested class",))
    assert dominates(rbh, fic) and not dominates(fic, rbh)


def test_the_frontier_drops_a_fiction_below_a_real_but_hard_route():
    class _I:
        def __init__(self, name, cv):
            self.name = name
            self.cost_vector = cv
    rbh = _I("rbh", CostVector(cash=5.0, hard_blockers=("needs a fume hood",)))
    fic = _I("fic", CostVector(cash=0.01, fiction_blockers=("unrecognized reaction type",)))
    assert {i.name for i in pareto_frontier([rbh, fic])} == {"rbh"}   # tier beats price


def test_a_fiction_rides_the_distinct_channel_not_hard_blockers():
    # isopentyl acetate's frontier is all C-C-fusion fiction (R55/R56): each entry now carries the reaction-type
    # blocker on ``fiction_blockers`` (disposition NOT_A_REACTION), and NOT on ``hard_blockers`` (the two are disjoint).
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    fr = resp.affordability_frontier
    assert fr
    saw_fiction = False
    for e in fr:
        cv = e.cost_vector
        assert not any("unrecognized reaction type" in b for b in cv.hard_blockers), "fiction leaked into hard_blockers"
        if cv.disposition is Disposition.NOT_A_REACTION:
            saw_fiction = True
            assert any("unrecognized reaction type" in b for b in cv.fiction_blockers)
    assert saw_fiction, "no fiction on the isopentyl-acetate frontier -- the classification consumer is vacuous"


def test_the_disposition_round_trips_through_the_replay_payload():
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    fr = resp.affordability_frontier
    assert fr
    for e in fr:
        back = affordability_entry_from_payload(affordability_entry_to_payload(e))
        assert back.cost_vector.disposition is e.cost_vector.disposition
        assert back.cost_vector.fiction_blockers == e.cost_vector.fiction_blockers
        assert back.cost_vector.hard_blockers == e.cost_vector.hard_blockers
        assert back.digest == e.digest        # the split field is part of identity (ranking-load-bearing, not hidden)


def test_a_centerless_pre_disposition_payload_still_revives():
    # a pre-R59 payload lacks the ``fiction_blockers`` key; ``.get`` tolerance revives it (empty fiction channel).
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    e = resp.affordability_frontier[0]
    pay = affordability_entry_to_payload(e)
    del pay["cost_vector"]["fiction_blockers"]
    revived = affordability_entry_from_payload(pay)
    assert revived.cost_vector.fiction_blockers == ()
    assert revived.cost_vector.disposition in (Disposition.CLEAN, Disposition.REAL_BUT_HARD)


def test_the_ranking_effect_is_honestly_data_dark_today():
    # the headline finding, pinned: with no real-but-hard route reachable, the 3-tier ranking cannot differ from the
    # old 2-tier one -- verdict-neutral in production.  If this flips, a genuine ranking consumer appeared: re-state R59.
    dark = probe.ranking_effect_data_dark()
    assert dark["reachable_real_but_hard_routes"] == 0
    assert dark["frontier_membership_changed_targets"] == 0
    assert dark["ranking_verdict_neutral_in_production"] is True
