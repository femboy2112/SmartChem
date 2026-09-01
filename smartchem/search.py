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

__all__ = ["SearchStatus"]


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
    PARTIAL_MULTIPLE_LIMITS = "PARTIAL_MULTIPLE_LIMITS"  # more than one limit bit at once
