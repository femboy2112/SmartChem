"""Shared search-completeness vocabulary for every SmartChem bounded search.

The formula decompiler (elemental descent), the linear route search, and the convergent-DAG search are three
different bounded enumerations, but they answer the SAME auditable question: did the search exhaust its declared
space, or stop early at a budget or result cap?  This module holds the one status vocabulary they share, so a
future unified response (CLI-JSON-01 / the shared ``CompilationResponse``) can speak of "the search" without
caring which kind produced it.

It is a low-level leaf module (standard library only), so both the top-level :mod:`smartchem.decompiler` and the
higher :mod:`smartchem.experiment` package can import it without a layering cycle.
"""
from __future__ import annotations

from enum import Enum

__all__ = ["SearchStatus", "STANDARD_8_2_STATUSES", "primary_standard_status"]


class SearchStatus(str, Enum):
    """Whether a declared bounded search actually exhausted its admitted candidate space.

    ``COMPLETE_WITHIN_BOUNDS`` never means complete chemistry -- only exhaustive within the search's OWN declared
    grammar, depth, and budgets.  The ``PARTIAL_*`` members name WHY a search stopped early, so a partial result
    is never laundered into a certified no-route (standard section 8; the decompiler's W2 wall).

    The budget members are deliberately kind-specific rather than one blurred "budget": a scission enumeration
    stops on a *cut* budget, a graph descent stops on a *search-node* budget, and calling both the same thing
    would hide which knob the caller must raise to make the search complete.
    """

    COMPLETE_WITHIN_BOUNDS = "COMPLETE_WITHIN_BOUNDS"
    PARTIAL_CUT_BUDGET = "PARTIAL_CUT_BUDGET"            # a scission/candidate enumeration hit its cut budget
    PARTIAL_SEARCH_BUDGET = "PARTIAL_SEARCH_BUDGET"      # a graph descent hit its search-node budget
    PARTIAL_RESULT_LIMIT = "PARTIAL_RESULT_LIMIT"        # the result/edge cap saturated before exhaustion
    PARTIAL_DEPTH_LIMIT = "PARTIAL_DEPTH_LIMIT"          # an expandable branch was cut by the max-depth bound
    PARTIAL_MULTIPLE_LIMITS = "PARTIAL_MULTIPLE_LIMITS"  # more than one limit bit at once

    # ``PARTIAL_DEPTH_LIMIT`` is this codebase's name for the standard's INCOMPLETE_DEPTH_LIMIT (section 8.2): a
    # retrosynthetic branch that COULD have been expanded (a linear-expandable single missing precursor, or any
    # missing precursor for the convergent DAG search) but was not, because the recursion hit ``max_depth``.
    # Without it a depth-truncated search reported COMPLETE_WITHIN_BOUNDS and its missed-but-reachable routes
    # vanished silently -- the exact "incomplete looks complete" defect section 8 forbids.  It is DISTINCT from a
    # grammar boundary (a linear search dropping a >=2-missing convergent branch is out-of-grammar, not
    # depth-limited) and from a genuine dead end (a node with no cleavages at all is complete, not truncated).

    @property
    def standard_name(self) -> "str | None":
        """This member's name in the standard's section 8.2 terminal-status vocabulary, or ``None``.

        ``None`` is returned only for ``PARTIAL_MULTIPLE_LIMITS``: section 8.2 requires exactly ONE primary stop
        reason, and the bare enum member -- which says only "more than one limit bit" -- cannot name it.  A
        SearchReceipt resolves its own primary from its recorded per-limit flags via
        :func:`primary_standard_status`; see the module-level reconciliation note for the full non-1:1 map.
        """
        return _STANDARD_NAME_BY_MEMBER[self]


# -- Section 8.2 status reconciliation ----------------------------------------------------------------------------
# The chemical-compiler standard (v0.5.0a1, section 8.2) fixes the canonical terminal-status vocabulary every
# SearchReceipt.status must speak.  This engine's SearchStatus is richer and older; the two are reconciled
# ADDITIVELY here (no rename -- SearchStatus is referenced across the decompiler, routes, DAG, and IR layers) via
# ``SearchStatus.standard_name`` plus ``primary_standard_status`` for the multiple-limit case.  The map is NON-1:1
# in BOTH directions, and BOTH residues are deliberate and documented:
#
#   engine -> 8.2  (two engine budget members collapse onto one 8.2 status):
#     COMPLETE_WITHIN_BOUNDS   -> COMPLETE_WITHIN_DECLARED_SPACE
#     PARTIAL_CUT_BUDGET       -> INCOMPLETE_CUT_BUDGET
#     PARTIAL_SEARCH_BUDGET    -> INCOMPLETE_CUT_BUDGET   (8.2 has ONE budget status; both engine budgets are
#                                                          genuine per-node cut/scission-enumeration budgets. Which
#                                                          knob to RAISE is named by the receipt's search_kind --
#                                                          FORMULA_DECOMPOSITION's `budget` vs the route/DAG
#                                                          `cut_budget_per_expansion` -- and by the retained native
#                                                          `status`; NOT by cut_budget_scope, which is uniformly
#                                                          PER_NODE on every current receipt and is a global-vs-
#                                                          per-node axis orthogonal to the cut-vs-search distinction)
#     PARTIAL_RESULT_LIMIT     -> INCOMPLETE_RESULT_LIMIT
#     PARTIAL_DEPTH_LIMIT      -> INCOMPLETE_DEPTH_LIMIT
#     PARTIAL_MULTIPLE_LIMITS  -> None                    (no single 8.2 name; a receipt resolves the primary
#                                                          from its own recorded limit flags -- see below)
#
#   8.2 -> engine  (these 8.2 statuses have no engine SearchStatus source in THIS engine):
#     INCOMPLETE_CANDIDATE_LIMIT   -- no search here stops on a distinct emitted-candidate cap; the caps that DO
#                                     bite are the cut budget and the result limit, already mapped above
#     REFUSED_INVALID_REQUEST      -- an invalid/unsupported request currently RAISES (an exception) rather than
#     REFUSED_IDENTITY_UNSUPPORTED -- returning a REFUSED_* receipt (e.g. decompiler.py refusing a charged target,
#                                     the formula<->structure gate).  Section 8.1 mandates a SearchReceipt even on
#                                     refusal, so this is an ACKNOWLEDGED, not-yet-built section 8.1 gap -- NOT a
#     ERROR_INTERNAL               -- conformant "by design" choice; an internal error likewise propagates as an
#                                     exception, not a terminal status.  Building the receipt-returning refusal
#                                     path (so REFUSED_*/ERROR_INTERNAL gain a real source) is a separate brick.
STANDARD_8_2_STATUSES = (
    "COMPLETE_WITHIN_DECLARED_SPACE",
    "INCOMPLETE_CUT_BUDGET",
    "INCOMPLETE_DEPTH_LIMIT",
    "INCOMPLETE_CANDIDATE_LIMIT",
    "INCOMPLETE_RESULT_LIMIT",
    "REFUSED_INVALID_REQUEST",
    "REFUSED_IDENTITY_UNSUPPORTED",
    "ERROR_INTERNAL",
)

_STANDARD_NAME_BY_MEMBER = {
    SearchStatus.COMPLETE_WITHIN_BOUNDS: "COMPLETE_WITHIN_DECLARED_SPACE",
    SearchStatus.PARTIAL_CUT_BUDGET: "INCOMPLETE_CUT_BUDGET",
    SearchStatus.PARTIAL_SEARCH_BUDGET: "INCOMPLETE_CUT_BUDGET",
    SearchStatus.PARTIAL_RESULT_LIMIT: "INCOMPLETE_RESULT_LIMIT",
    SearchStatus.PARTIAL_DEPTH_LIMIT: "INCOMPLETE_DEPTH_LIMIT",
    SearchStatus.PARTIAL_MULTIPLE_LIMITS: None,
}

# Precedence for resolving PARTIAL_MULTIPLE_LIMITS to one section 8.2 primary.  Section 8.2 requires exactly one
# primary stop reason even when several limits bit, but fixes NO precedence -- it leaves the choice to the
# implementation and still records every co-firing limit on the receipt's own flags.  So this order is purely a
# documented REPORTING convention, not a chemistry claim and not something section 8.2's text constrains.  It runs
# from the most to the least severe incompleteness: a cut/search-budget stop truncated the candidate ENUMERATION
# itself (most fundamental); a depth stop cut an expandable branch at the depth bound; a result-limit stop is
# ranked least severe because the search stayed productive up to its declared OUTPUT budget.  (Caveat, honest: for
# the DAG search result_limit_saturated is CONSERVATIVE -- it can also fire when an intermediate recursion level
# filled max_dags and stopped enumerating, so `candidate_enumeration_complete` treats it as enumeration not
# finishing; ranking it last is a severity convention, not a claim that enumeration always completed.)  Every
# outcome is one of the four INCOMPLETE_* names, so the primary is never laundered toward "more complete".
_PRIMARY_PRECEDENCE = (
    SearchStatus.PARTIAL_CUT_BUDGET,
    SearchStatus.PARTIAL_SEARCH_BUDGET,
    SearchStatus.PARTIAL_DEPTH_LIMIT,
    SearchStatus.PARTIAL_RESULT_LIMIT,
)


def primary_standard_status(active: "tuple[SearchStatus, ...]") -> str:
    """Resolve the individual limits that fired at once to the single section 8.2 primary stop reason.

    ``active`` is the concrete ``PARTIAL_*`` limits that bit -- never ``COMPLETE_WITHIN_BOUNDS`` or
    ``PARTIAL_MULTIPLE_LIMITS`` itself.  Returns the section 8.2 name of the highest-precedence member per
    :data:`_PRIMARY_PRECEDENCE`.  Raises :class:`ValueError` on an empty set: a ``PARTIAL_MULTIPLE_LIMITS`` receipt
    with no recorded limits is a receipt bug, not a status to launder into "complete".
    """
    active_set = set(active)
    for member in _PRIMARY_PRECEDENCE:
        if member in active_set:
            return _STANDARD_NAME_BY_MEMBER[member]
    raise ValueError("no active limit to resolve to a section 8.2 primary stop reason")
