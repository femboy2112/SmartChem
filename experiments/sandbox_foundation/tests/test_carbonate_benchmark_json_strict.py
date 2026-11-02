"""Strict cross-language JSON contract for the committed carbonate/CO2 PHREEQC reference table.

Same blunt contract as the acetate reference (`test_benchmark_json_strict.py`): no nonfinite tokens survive, the
table is portable strict JSON, and every scored row carries a finite dpH and a valid class.  A single small read --
no PHREEQC, no recompute.
"""
import json
import math
from pathlib import Path

TABLE = Path(__file__).parent.parent / "benchmarks" / "carbonate_phreeqc" / "comparison_table.json"
_CLASSES = {"AGREE", "MARGINAL", "DIVERGE"}


def _reject(x):
    raise AssertionError(f"nonfinite JSON constant present: {x!r}")


def test_no_nonfinite_tokens_in_raw_text():
    text = TABLE.read_text()
    for tok in ("NaN", "Infinity", "-Infinity"):
        assert tok not in text, f"forbidden token {tok!r} present in {TABLE.name}"


def test_parses_under_strict_constant_rejecting_parser():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    assert isinstance(obj, dict) and obj["rows"]


def test_round_trips_without_allow_nan():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    json.loads(json.dumps(obj, allow_nan=False))


def test_database_provenance_recorded():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    assert obj["database"] == "phreeqc.dat"
    assert len(obj["database_sha256"]) == 64 and all(c in "0123456789abcdef" for c in obj["database_sha256"])


def test_every_scored_row_has_finite_dph_and_valid_class():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    scored = [r for r in obj["rows"].values() if "dpH" in r]
    assert scored, "no scored rows"
    for r in scored:
        assert isinstance(r["dpH"], float) and math.isfinite(r["dpH"]) and r["dpH"] >= 0
        assert r["class"] in _CLASSES
    # worst_dpH is the honest max over scored rows.
    assert obj["worst_dpH"] == max(r["dpH"] for r in scored)


def test_no_divergence_in_the_committed_reference():
    # The committed benchmark is VERIFICATION-grade: every case is AGREE or MARGINAL (activity-model gap), never a
    # DIVERGE (which would signal a real equation/constant error).  If a future constant edit breaks this, it SHOULD
    # go red here.
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    diverged = [cid for cid, r in obj["rows"].items() if r.get("class") == "DIVERGE"]
    assert not diverged, f"unexpected DIVERGE cases in the committed reference: {diverged}"
