"""SRCH-NO-01: the section-8.3 four-outcome no-route matrix, surfaced uniformly across every renderer + --json.

Pins: (1) the pure ``section_8_3_label`` leaf over the full 2x2 + its negative guard; (2) the LOAD-BEARING
service-level distinction -- an empty COMPLETE search is ``NO_ROUTE_IN_DECLARED_SPACE`` while an empty INCOMPLETE
search is ``INCOMPLETE_NO_ROUTE_OBSERVED`` (absence OBSERVED, never laundered into a certified no-route); (3) the
label rides the --json payload AND the human render identically (the uniform surfacing the brick exists to deliver).
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.search import (
    COMPLETE_CANDIDATE_SET,
    INCOMPLETE_NO_ROUTE_OBSERVED,
    NO_ROUTE_IN_DECLARED_SPACE,
    PARTIAL_CANDIDATE_SET,
    section_8_3_label,
)
from smartchem.service import build_recompile_request, run_compilation


def test_the_pure_label_covers_the_full_2x2():
    assert section_8_3_label(True, 0) == NO_ROUTE_IN_DECLARED_SPACE
    assert section_8_3_label(False, 0) == INCOMPLETE_NO_ROUTE_OBSERVED
    assert section_8_3_label(True, 3) == COMPLETE_CANDIDATE_SET
    assert section_8_3_label(False, 3) == PARTIAL_CANDIDATE_SET


def test_a_negative_count_is_a_caller_bug_not_a_fifth_outcome():
    with pytest.raises(ValueError):
        section_8_3_label(True, -1)


def test_empty_incomplete_is_never_laundered_into_a_complete_no_route():
    # The load-bearing distinction. A shallow, cut-starved paracetamol search returns NO candidate AND is INCOMPLETE
    # -- it must read INCOMPLETE_NO_ROUTE_OBSERVED, distinct from the complete-empty no-route ([[vacuous-green]] kin:
    # an incomplete empty search that reads as a certified no-route is exactly the section-8 truth hole).
    resp = run_compilation(build_recompile_request("paracetamol", max_depth=1, cut_budget=1))
    assert resp.compilation_ir.candidate_count == 0 and not resp.compilation_ir.complete_within_bounds
    assert resp.search_space_status == INCOMPLETE_NO_ROUTE_OBSERVED


def test_empty_complete_is_the_real_no_route_in_declared_space():
    # elements-only (commodities off) acetic anhydride at depth 2: a COMPLETE, empty declared space.
    resp = run_compilation(build_recompile_request("acetic anhydride", commodities_enabled=False, max_depth=2))
    assert resp.compilation_ir.candidate_count == 0 and resp.compilation_ir.complete_within_bounds
    assert resp.search_space_status == NO_ROUTE_IN_DECLARED_SPACE


def test_the_two_empty_cells_get_distinct_labels():
    incomplete = run_compilation(build_recompile_request("paracetamol", max_depth=1, cut_budget=1))
    complete = run_compilation(build_recompile_request("acetic anhydride", commodities_enabled=False, max_depth=2))
    # the coarsity the brick removes: both were "empty", but they are NOT the same outcome.
    assert incomplete.search_space_status != complete.search_space_status
    assert incomplete.search_space_status == INCOMPLETE_NO_ROUTE_OBSERVED
    assert complete.search_space_status == NO_ROUTE_IN_DECLARED_SPACE


def test_a_refusal_carries_no_search_space_label():
    resp = run_compilation(build_recompile_request("not-a-real-name-zzz"))
    assert resp.compilation_ir is None
    assert resp.search_space_status is None  # no bounded search ran -> no section-8.3 label to make


def _cli_capture(argv: list[str]) -> "tuple[int, str]":
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def test_the_label_rides_both_the_human_render_and_json_identically():
    # SRCH-NO-01's whole point: uniform across views.  The incomplete-empty cell surfaces the SAME token in both,
    # so a consumer can never read "no route" on one view while the other says the search never finished.
    argv = ["recompile", "paracetamol", "--max-depth", "1", "--cut-budget", "1"]
    _, human = _cli_capture(argv)
    _, jout = _cli_capture([*argv, "--json"])
    label = json.loads(jout)["search_space_status"]
    assert label == INCOMPLETE_NO_ROUTE_OBSERVED
    assert label in human  # the literal token -- not a vague "PARTIAL" -- reaches the human render too
