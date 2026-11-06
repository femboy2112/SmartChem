"""Strict cross-language JSON contract for the pinned PHREEQC reference table.

Python's json.load is permissive -- it happily swallows bare NaN/Infinity tokens
that every strict parser (and every other language) rejects. This committed
reference is read by ion_pair_comparison.py and is meant to be portable, so the
contract here is blunt: no nonfinite tokens survive, the undefined cells are typed
nulls with a stated reason, and the defined cells are honest finite floats. A single
small read -- no heavy imports, no PHREEQC, no recompute.
"""
import json
import math
from pathlib import Path

TABLE = Path(__file__).parent.parent / "benchmarks" / "acetate_phreeqc" / "comparison_table.json"


def _reject(x):
    # parse_constant fires only on NaN/Infinity/-Infinity; reaching it at all is the failure.
    raise AssertionError(f"nonfinite JSON constant present: {x!r}")


def test_no_nonfinite_tokens_in_raw_text():
    text = TABLE.read_text()
    for tok in ("NaN", "Infinity", "-Infinity"):
        assert tok not in text, f"forbidden token {tok!r} present in {TABLE.name}"


def test_parses_under_strict_constant_rejecting_parser():
    text = TABLE.read_text()
    obj = json.loads(text, parse_constant=_reject)   # raises via _reject if any nonfinite slips through
    assert isinstance(obj, list) and obj


def test_round_trips_without_allow_nan():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    json.loads(json.dumps(obj, allow_nan=False))     # dumps raises if any value is nonfinite; re-parse confirms


def test_ct0_rows_are_typed_nulls_with_reason():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    ct0 = [r for r in obj if r["CT"] == 0]
    assert len(ct0) == 2, f"expected exactly 2 CT==0 rows, found {len(ct0)}"
    for r in ct0:
        assert r["dAc"] is None and r["dHAc"] is None
        assert r["rel_err_undefined_reason"] == "REFERENCE_SPECIES_ABSENT"


def test_ct_positive_rows_have_finite_errors():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    for r in obj:
        if r["CT"] > 0:
            assert isinstance(r["dAc"], float) and math.isfinite(r["dAc"])
            assert isinstance(r["dHAc"], float) and math.isfinite(r["dHAc"])
