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

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "SearchStatus",
    "STANDARD_8_2_STATUSES",
    "PRIMARY_RESOLVABLE_8_2_STATUSES",
    "primary_standard_status",
    "REFUSED_8_2_STATUSES",
    "ERROR_8_2_STATUSES",
    "NON_SEARCH_8_2_STATUSES",
    "RefusalReceipt",
    "NO_ROUTE_IN_DECLARED_SPACE",
    "INCOMPLETE_NO_ROUTE_OBSERVED",
    "COMPLETE_CANDIDATE_SET",
    "PARTIAL_CANDIDATE_SET",
    "STANDARD_8_3_LABELS",
    "SECTION_8_3_NOTE",
    "section_8_3_label",
]


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
#   8.2 -> engine  (these 8.2 statuses are NOT SearchStatus members -- they live on a different axis):
#     REFUSED_INVALID_REQUEST      -- NOW SOURCED, not by a SearchStatus but by a RefusalReceipt on the refusal
#     REFUSED_IDENTITY_UNSUPPORTED -- axis (see the RefusalReceipt note below).  A receipt-returning front door
#                                     (decompiler.decompile_or_refuse) catches the engine's raised refusal and
#                                     returns a RefusalReceipt carrying the section 8.2 name: a malformed request
#                                     -> REFUSED_INVALID_REQUEST, an unsupported chemical identity (a charged
#                                     target, via IdentityUnsupportedError) -> REFUSED_IDENTITY_UNSUPPORTED.  The
#                                     low-level raising API is unchanged; the front door SOURCES the section 8.2
#                                     STATUS on the refusal axis (it does not yet emit the full section 8.1
#                                     SearchReceipt schema on refusal -- that null-counter step is a later brick).
#     INCOMPLETE_CANDIDATE_LIMIT   -- still no engine source: no search here stops on a distinct emitted-candidate
#                                     cap; the caps that DO bite are the cut budget and the result limit (mapped
#                                     above).  This one really is a SearchStatus gap, not a refusal-axis one.
#     ERROR_INTERNAL               -- still no engine source in THIS layer: an internal error propagates as an
#                                     exception.  Turning an uncaught bug into an ERROR_INTERNAL RefusalReceipt is
#                                     the province of a top-level guarded service (a later brick), not a domain
#                                     front door, which catches only DecompilerError (a chemical-domain refusal).
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


# -- Section 8.3 no-route matrix ----------------------------------------------------------------------------------
# Section 8.3 fixes a SECOND axis, orthogonal to the 8.2 stop-reason above: what the (candidates present?, search
# complete?) pair MEANS to a user.  The 2x2 has exactly four user-facing outcomes, and the standard forbids the
# bare phrase "no route found" without the receipt state -- so every PUBLIC CLI renderer (the recompile + decompile
# --json/human views via ``CompilationResponse.search_space_status``, and the compile/synthesize Dossier) routes its
# outcome wording through the ONE function below, and the four labels read UNIFORMLY across those surfaces
# (SRCH-NO-01).  The load-bearing distinction is empty-COMPLETE (a real no-route) vs empty-INCOMPLETE (absence
# observed, nothing proven) -- an incomplete empty search must NEVER be laundered into a certified no-route.
NO_ROUTE_IN_DECLARED_SPACE = "NO_ROUTE_IN_DECLARED_SPACE"      # no candidates, search COMPLETE
INCOMPLETE_NO_ROUTE_OBSERVED = "INCOMPLETE_NO_ROUTE_OBSERVED"  # no candidates, search INCOMPLETE (absence != evidence)
COMPLETE_CANDIDATE_SET = "COMPLETE_CANDIDATE_SET"              # candidate(s) present, search COMPLETE
PARTIAL_CANDIDATE_SET = "PARTIAL_CANDIDATE_SET"                # candidate(s) present, search INCOMPLETE

STANDARD_8_3_LABELS = (
    NO_ROUTE_IN_DECLARED_SPACE,
    INCOMPLETE_NO_ROUTE_OBSERVED,
    COMPLETE_CANDIDATE_SET,
    PARTIAL_CANDIDATE_SET,
)


def section_8_3_label(complete_within_bounds: bool, candidate_count: int) -> str:
    """The one section-8.3 user-facing label for a ``(complete_within_bounds, candidate_count)`` pair.

    The standard's 2x2 (section 8.3): an EMPTY search that was COMPLETE is a real
    ``NO_ROUTE_IN_DECLARED_SPACE``; an EMPTY search that was INCOMPLETE only OBSERVED no route and proved nothing
    (``INCOMPLETE_NO_ROUTE_OBSERVED`` -- absence is not evidence); a non-empty COMPLETE search is a
    ``COMPLETE_CANDIDATE_SET``; a non-empty INCOMPLETE one is a ``PARTIAL_CANDIDATE_SET``.  Every renderer routes
    through this so the incomplete-empty cell is never collapsed into (nor laundered as) the complete-empty
    no-route cell.  ``candidate_count`` is a count, so a negative value is a caller bug, not a fifth outcome.
    """
    if candidate_count < 0:
        raise ValueError("candidate_count cannot be negative")
    if candidate_count == 0:
        return NO_ROUTE_IN_DECLARED_SPACE if complete_within_bounds else INCOMPLETE_NO_ROUTE_OBSERVED
    return COMPLETE_CANDIDATE_SET if complete_within_bounds else PARTIAL_CANDIDATE_SET


# The ONE human note per section-8.3 label, shared by every renderer so the wording cannot drift between the
# recompile, decompile, and compile surfaces (SRCH-NO-01).  Keyed by the label so a caller writes
# ``f"{label}: {SECTION_8_3_NOTE[label]}"`` and the four outcomes always read identically.
SECTION_8_3_NOTE = {
    NO_ROUTE_IN_DECLARED_SPACE: (
        "no route within the declared bounded search space; the search was COMPLETE, so this is a real absence "
        "in the current grammar/bounds -- not a claim about chemistry outside them"
    ),
    INCOMPLETE_NO_ROUTE_OBSERVED: (
        "no route was OBSERVED, but the search was INCOMPLETE -- absence is not evidence; raise the search "
        "budget/depth bounds or widen the inventory before concluding no route exists"
    ),
    COMPLETE_CANDIDATE_SET: "candidate route(s) found; the search was COMPLETE within the declared bounds",
    PARTIAL_CANDIDATE_SET: (
        "candidate route(s) found, but the search was INCOMPLETE -- more may exist beyond the declared bounds; "
        "raise the search budget/depth bounds to search further"
    ),
}


# The exact section 8.2 names PARTIAL_MULTIPLE_LIMITS can resolve to via primary_standard_status -- derived from
# the precedence, so it never drifts.  A consumer that stores a resolved primary (e.g. the IR, whose search_status
# is a bare enum lacking the per-limit flags) uses this to check that a MULTIPLE status resolved to a legal
# primary and not, say, INCOMPLETE_CANDIDATE_LIMIT (which no engine limit produces).
PRIMARY_RESOLVABLE_8_2_STATUSES = frozenset(_STANDARD_NAME_BY_MEMBER[m] for m in _PRIMARY_PRECEDENCE)


# -- Section 8.1 receipt on a REFUSED/ERROR request (the non-search terminal outcomes) ----------------------------
# Section 8.1 mandates a receipt even when a request produces NO bounded search: a request that is refused or
# errors out before searching.  The section 8.2 statuses for that case (REFUSED_*/ERROR_INTERNAL) live on a
# DIFFERENT AXIS than search completeness.  SearchStatus answers "did the search exhaust its declared space?"; a
# refused request never produced a search to ask that of.  So these are deliberately NOT SearchStatus members --
# adding them would silently mis-bucket a refusal in every "COMPLETE_WITHIN_BOUNDS else treat-as-partial" branch
# that reads a SearchStatus.  Instead a receipt-returning front door catches the engine's raised refusal and
# packages it here, carrying the section 8.2 name directly.
REFUSED_8_2_STATUSES = frozenset({"REFUSED_INVALID_REQUEST", "REFUSED_IDENTITY_UNSUPPORTED"})
ERROR_8_2_STATUSES = frozenset({"ERROR_INTERNAL"})
#: The section 8.2 statuses a bounded search never produces -- the terminal outcomes of a request that did not
#: search.  Exactly the RefusalReceipt-admissible statuses; disjoint from the SearchStatus image by construction.
NON_SEARCH_8_2_STATUSES = REFUSED_8_2_STATUSES | ERROR_8_2_STATUSES


@dataclass(frozen=True)
class RefusalReceipt:
    """The section 8.2 terminal status of a request REFUSED or ERRORED before it produced any bounded search.

    This is the refusal-axis outcome that gives section 8.2's ``REFUSED_*`` names a real return-path source: a
    receipt-returning front door catches the engine's raised refusal and carries the section 8.2 name here instead
    of letting it escape as a bare exception.  It is deliberately MINIMAL and is NOT the full section 8.1
    ``SearchReceipt`` schema (the ~20 mandated counters): on a refusal no search ran, so those counters are all
    "not applicable", and emitting a full SearchReceipt-on-refusal with them pinned to UNKNOWN/None is a further
    step (tracked in the uptake manifest).  What this value DOES guarantee is the two things section 8 most cares
    about: a refusal never escapes with NO terminal status, and it never borrows a search-completeness status it
    did not earn.

    ``standard_status`` is a section 8.2 ``REFUSED_*``/``ERROR_INTERNAL`` name, kept in a type separate from the
    ``SearchStatus`` completeness receipts on purpose (see the reconciliation note above).  ``reason`` is the
    human-readable cause (typically the raised message); ``request`` echoes the offending request for the audit
    trail.  A RefusalReceipt carries no candidate digest -- a refusal enumerated nothing, and pretending otherwise
    would be the exact "incomplete looks complete" defect section 8 forbids, one axis over.
    """

    standard_status: str
    reason: str
    request: str = ""

    def __post_init__(self) -> None:
        if self.standard_status not in NON_SEARCH_8_2_STATUSES:
            raise ValueError(
                "a RefusalReceipt.standard_status must be a section 8.2 refusal/error status (one of "
                f"{sorted(NON_SEARCH_8_2_STATUSES)}), got {self.standard_status!r}; a completed or partial search "
                "is a SearchStatus receipt, not a refusal"
            )
        if not self.reason.strip():
            raise ValueError("a RefusalReceipt must state a human-readable reason for the refusal")

    @property
    def is_refusal(self) -> bool:
        """True for a REFUSED_* request (a chemical-domain refusal), False for an ERROR_INTERNAL one (a bug)."""
        return self.standard_status in REFUSED_8_2_STATUSES

    def render(self) -> str:
        """One-line audit rendering that leads with the section 8.2 status (never a bare native message).

        The lead word tracks :attr:`is_refusal`, so the rendering can never contradict the receipt's own
        classification: a ``REFUSED_*`` request reads ``refused:``; an ``ERROR_INTERNAL`` one reads ``error:``
        (an internal bug is not a chemical-domain refusal).
        """
        lead = "refused" if self.is_refusal else "error"
        head = f"{lead}: {self.standard_status}"
        if self.request:
            head += f" [{self.request}]"
        return f"{head} -- {self.reason}"
