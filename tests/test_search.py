"""Adversarial tests for the section 8.2 status-vocabulary reconciliation on :mod:`smartchem.search`.

The engine's :class:`SearchStatus` is richer and older than the chemical-compiler standard's section 8.2
terminal-status set; ``standard_name`` and ``primary_standard_status`` reconcile the two ADDITIVELY (no rename).
These tests pin the reconciliation as a TRIPWIRE: they fail loudly if a future enum member is added without a
section 8.2 mapping, if the documented non-1:1 residue shifts, or if the multiple-limit precedence drifts.
"""
from __future__ import annotations

from itertools import combinations

import pytest

from smartchem.search import (
    ERROR_8_2_STATUSES,
    NON_SEARCH_8_2_STATUSES,
    PRIMARY_RESOLVABLE_8_2_STATUSES,
    REFUSED_8_2_STATUSES,
    STANDARD_8_2_STATUSES,
    RefusalReceipt,
    SearchStatus,
    primary_standard_status,
)

# The four section 8.2 statuses this engine deliberately has NO SearchStatus source for (documented residue).
_RESIDUE_8_2 = {
    "INCOMPLETE_CANDIDATE_LIMIT",
    "REFUSED_INVALID_REQUEST",
    "REFUSED_IDENTITY_UNSUPPORTED",
    "ERROR_INTERNAL",
}
# The concrete PARTIAL_* limits a receipt can record simultaneously, in falling primary precedence.
_CONCRETE_LIMITS = (
    SearchStatus.PARTIAL_CUT_BUDGET,
    SearchStatus.PARTIAL_SEARCH_BUDGET,
    SearchStatus.PARTIAL_DEPTH_LIMIT,
    SearchStatus.PARTIAL_RESULT_LIMIT,
)


class TestStandardNameMap:
    def test_mapping_is_total_over_the_live_enum(self):
        # A future SearchStatus member added without a mapping entry raises KeyError here -- the tripwire.
        for member in SearchStatus:
            _ = member.standard_name  # must not raise

    def test_image_is_a_subset_of_the_8_2_vocabulary(self):
        image = {m.standard_name for m in SearchStatus if m.standard_name is not None}
        assert image <= set(STANDARD_8_2_STATUSES)

    def test_no_8_2_name_is_misspelled(self):
        # every mapped name is a real 8.2 member (catches a typo that would silently leave the vocabulary)
        for member in SearchStatus:
            if member.standard_name is not None:
                assert member.standard_name in STANDARD_8_2_STATUSES

    def test_8_2_vocabulary_has_exactly_eight_distinct_members(self):
        assert len(STANDARD_8_2_STATUSES) == len(set(STANDARD_8_2_STATUSES)) == 8

    def test_documented_residue_is_exactly_the_four_unsourced_statuses(self):
        # pins the non-1:1-ness: if someone later wires one of these to an engine member, this bites so the
        # module's reconciliation note gets updated in lockstep -- and vice versa.
        image = {m.standard_name for m in SearchStatus if m.standard_name is not None}
        assert set(STANDARD_8_2_STATUSES) - image == _RESIDUE_8_2

    def test_two_budget_members_collapse_onto_one_8_2_status(self):
        assert (
            SearchStatus.PARTIAL_CUT_BUDGET.standard_name
            == SearchStatus.PARTIAL_SEARCH_BUDGET.standard_name
            == "INCOMPLETE_CUT_BUDGET"
        )

    def test_multiple_limits_is_the_only_member_without_a_single_8_2_name(self):
        none_members = [m for m in SearchStatus if m.standard_name is None]
        assert none_members == [SearchStatus.PARTIAL_MULTIPLE_LIMITS]

    def test_complete_and_the_single_limits_map_as_documented(self):
        assert SearchStatus.COMPLETE_WITHIN_BOUNDS.standard_name == "COMPLETE_WITHIN_DECLARED_SPACE"
        assert SearchStatus.PARTIAL_RESULT_LIMIT.standard_name == "INCOMPLETE_RESULT_LIMIT"
        assert SearchStatus.PARTIAL_DEPTH_LIMIT.standard_name == "INCOMPLETE_DEPTH_LIMIT"


class TestPrimaryStandardStatus:
    def test_cut_budget_wins_over_result_limit(self):
        assert primary_standard_status(
            (SearchStatus.PARTIAL_RESULT_LIMIT, SearchStatus.PARTIAL_CUT_BUDGET)
        ) == "INCOMPLETE_CUT_BUDGET"

    def test_depth_wins_over_result_but_loses_to_budget(self):
        assert primary_standard_status(
            (SearchStatus.PARTIAL_DEPTH_LIMIT, SearchStatus.PARTIAL_RESULT_LIMIT)
        ) == "INCOMPLETE_DEPTH_LIMIT"
        assert primary_standard_status(
            (SearchStatus.PARTIAL_DEPTH_LIMIT, SearchStatus.PARTIAL_SEARCH_BUDGET)
        ) == "INCOMPLETE_CUT_BUDGET"

    def test_result_limit_alone_resolves_to_itself(self):
        assert primary_standard_status((SearchStatus.PARTIAL_RESULT_LIMIT,)) == "INCOMPLETE_RESULT_LIMIT"

    def test_order_of_the_input_does_not_matter(self):
        forward = primary_standard_status((SearchStatus.PARTIAL_CUT_BUDGET, SearchStatus.PARTIAL_DEPTH_LIMIT))
        reverse = primary_standard_status((SearchStatus.PARTIAL_DEPTH_LIMIT, SearchStatus.PARTIAL_CUT_BUDGET))
        assert forward == reverse == "INCOMPLETE_CUT_BUDGET"

    def test_every_nonempty_subset_resolves_to_a_valid_8_2_status(self):
        # adversarial: over ALL 15 non-empty subsets of the concrete limits, the resolver must return a real 8.2
        # member (never None, never off-vocabulary) and specifically the highest-precedence one present.
        for size in range(1, len(_CONCRETE_LIMITS) + 1):
            for subset in combinations(_CONCRETE_LIMITS, size):
                got = primary_standard_status(subset)
                assert got in STANDARD_8_2_STATUSES
                expected = next(m.standard_name for m in _CONCRETE_LIMITS if m in set(subset))
                assert got == expected

    def test_empty_active_set_raises(self):
        with pytest.raises(ValueError, match="no active limit"):
            primary_standard_status(())

    def test_non_limit_members_do_not_resolve(self):
        # COMPLETE / MULTIPLE are not primary-resolvable limits; a set of only those is a receipt bug, not a
        # status to launder into "complete".
        with pytest.raises(ValueError, match="no active limit"):
            primary_standard_status((SearchStatus.COMPLETE_WITHIN_BOUNDS,))
        with pytest.raises(ValueError, match="no active limit"):
            primary_standard_status((SearchStatus.PARTIAL_MULTIPLE_LIMITS,))


class TestRefusalReceiptVocabulary:
    """The section 8.1 refusal-axis vocabulary: REFUSED_*/ERROR_INTERNAL are the terminal statuses of a request
    that produced NO search, and are held in a type separate from the SearchStatus completeness receipts."""

    def test_the_non_search_statuses_are_exactly_refused_plus_error(self):
        assert NON_SEARCH_8_2_STATUSES == REFUSED_8_2_STATUSES | ERROR_8_2_STATUSES
        assert REFUSED_8_2_STATUSES == {"REFUSED_INVALID_REQUEST", "REFUSED_IDENTITY_UNSUPPORTED"}
        assert ERROR_8_2_STATUSES == {"ERROR_INTERNAL"}

    def test_refusal_statuses_are_real_8_2_members(self):
        assert NON_SEARCH_8_2_STATUSES <= set(STANDARD_8_2_STATUSES)

    def test_refusal_axis_is_disjoint_from_the_search_completeness_image(self):
        # load-bearing "different axis" claim: nothing a SearchStatus resolves to is a refusal status, and vice
        # versa. A refusal can never be spelled as a completeness verdict, or the two axes would collide.
        search_image = {m.standard_name for m in SearchStatus if m.standard_name is not None}
        assert search_image.isdisjoint(NON_SEARCH_8_2_STATUSES)
        assert PRIMARY_RESOLVABLE_8_2_STATUSES.isdisjoint(NON_SEARCH_8_2_STATUSES)

    def test_the_eight_8_2_statuses_partition_into_search_and_non_search(self):
        # every 8.2 status is either a search-completeness outcome (in the SearchStatus image OR the still-unsourced
        # INCOMPLETE_CANDIDATE_LIMIT) or a non-search outcome -- never both, never neither.
        search_image = {m.standard_name for m in SearchStatus if m.standard_name is not None}
        search_axis = search_image | {"INCOMPLETE_CANDIDATE_LIMIT"}
        assert search_axis.isdisjoint(NON_SEARCH_8_2_STATUSES)
        assert search_axis | NON_SEARCH_8_2_STATUSES == set(STANDARD_8_2_STATUSES)


class TestRefusalReceipt:
    def test_a_refused_receipt_carries_its_8_2_status_reason_and_echo(self):
        rc = RefusalReceipt("REFUSED_IDENTITY_UNSUPPORTED", "charged target", request="Na^1+")
        assert rc.standard_status == "REFUSED_IDENTITY_UNSUPPORTED"
        assert rc.reason == "charged target"
        assert rc.request == "Na^1+"
        assert rc.is_refusal is True

    def test_error_internal_is_admissible_but_is_not_a_refusal(self):
        rc = RefusalReceipt("ERROR_INTERNAL", "an internal invariant broke")
        assert rc.is_refusal is False  # a bug, not a chemical-domain refusal
        assert rc.request == ""  # request echo is optional

    @pytest.mark.parametrize("bad", ["COMPLETE_WITHIN_DECLARED_SPACE", "INCOMPLETE_CUT_BUDGET",
                                     "INCOMPLETE_RESULT_LIMIT", "PARTIAL_CUT_BUDGET", "nonsense", ""])
    def test_a_non_refusal_status_is_refused_at_construction(self, bad):
        # the guard's whole job: a completeness status (or garbage) can never masquerade as a refusal receipt.
        with pytest.raises(ValueError, match="refusal/error status"):
            RefusalReceipt(bad, "some reason")

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n "])
    def test_an_empty_or_whitespace_reason_is_refused(self, blank):
        # red-team: a whitespace-only reason is truthy but not "human-readable"; the guard must strip.
        with pytest.raises(ValueError, match="human-readable reason"):
            RefusalReceipt("REFUSED_INVALID_REQUEST", blank)

    def test_render_prefix_tracks_is_refusal(self):
        # red-team: render must never call an ERROR_INTERNAL (is_refusal False) a "refused:" outcome.
        assert RefusalReceipt("ERROR_INTERNAL", "internal invariant broke").render().startswith("error:")
        assert RefusalReceipt("REFUSED_IDENTITY_UNSUPPORTED", "charged").render().startswith("refused:")

    def test_render_leads_with_the_8_2_status(self):
        out = RefusalReceipt("REFUSED_IDENTITY_UNSUPPORTED", "charged", request="Na^+").render()
        assert out.startswith("refused: REFUSED_IDENTITY_UNSUPPORTED")
        assert "Na^+" in out and "charged" in out

    def test_the_receipt_is_frozen_and_hashable(self):
        rc = RefusalReceipt("ERROR_INTERNAL", "boom")
        with pytest.raises(Exception):
            rc.reason = "changed"  # type: ignore[misc]
        assert isinstance(hash(rc), int)
