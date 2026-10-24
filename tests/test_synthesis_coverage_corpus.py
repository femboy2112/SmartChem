"""Regression pin for SYNTHESIS-COVERAGE-CORPUS-01 (the campaign's recall / false-vouch baseline).

The corpus is the committed instrument; this gates its verdict in CI so a future change cannot silently drop
recall or -- the cardinal sin -- introduce a false-vouch on a fiction/mutation without turning this red.
"""
from __future__ import annotations

import experiments.synthesis_coverage_corpus as corpus


def test_corpus_baseline_full_recall_zero_false_vouch():
    m = corpus.measure()
    assert m["false_vouch"] == 0, f"FALSE-VOUCH regression: {m['rows']}"
    assert m["recall"] == m["positives"], f"recall regression: {m['recall']}/{m['positives']}"
    assert m["null_ok"] == m["totals"][corpus.NULL]
    assert m["mutation_ok"] == m["totals"][corpus.MUTATION]
    assert corpus.validate() is True
