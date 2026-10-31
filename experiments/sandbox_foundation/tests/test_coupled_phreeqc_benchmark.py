"""OPERATION XIII P0 -- the committed MIXED vinegar/bicarbonate benchmark artifacts (strict + honest-null contract).

PHREEQC is absent on the baseline, so unlike the acetate/carbonate tables this one has NO reference pH column: the
contract is that it stays HONESTLY NULL (EXTERNAL_VALIDATION_UNAVAILABLE), is portable strict JSON, carries the code
column + the arbitrary-precision holdout tier, demotes the out-of-domain case, and that the reproducible decks exist.
A single small read -- no PHREEQC, no recompute.
"""
from __future__ import annotations

import json
from pathlib import Path

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import EXTERNAL_VALIDATION_UNAVAILABLE, NUMERICALLY_UNVERIFIED
from experiments.sandbox_foundation.coupled_equilibrium import mixed_phreeqc_benchmark_obligation

BENCH = Path(__file__).parent.parent / "benchmarks" / "coupled_phreeqc"
TABLE = BENCH / "comparison_table.json"
CODE = BENCH / "code_results.json"


def _reject(x):
    raise AssertionError(f"nonfinite JSON constant present: {x!r}")


def test_tables_parse_under_a_strict_constant_rejecting_parser():
    for path in (TABLE, CODE):
        text = path.read_text()
        for tok in ("NaN", "Infinity", "-Infinity"):
            assert tok not in text, f"forbidden token {tok!r} in {path.name}"
        obj = json.loads(text, parse_constant=_reject)
        json.loads(json.dumps(obj, allow_nan=False))   # round-trips without allow_nan


def test_phreeqc_column_is_honestly_null_not_fabricated():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    assert obj["reference_status"] == EXTERNAL_VALIDATION_UNAVAILABLE
    for cid, row in obj["rows"].items():
        assert row["phreeqc_pH"] is None, f"{cid}: a PHREEQC pH appeared but PHREEQC was never run"
        assert row["abs_dpH"] is None


def test_code_column_and_holdout_tier_are_present_for_admitted_cases():
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    for cid, row in obj["rows"].items():
        if cid == "M11":
            continue
        assert isinstance(row["code_pH_davies"], float)
        assert row["hp_tier_davies"] == claim_tiers.NUMERICALLY_VERIFIED, cid


def test_out_of_domain_case_is_demoted_not_vouched():
    # M11 (I > 0.5 M) must carry the NUMERICALLY_UNVERIFIED verdict -- the solver demotes rather than extrapolate.
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    assert obj["rows"]["M11"]["code_verdict_davies"] == NUMERICALLY_UNVERIFIED


def test_bicarbonate_limited_case_is_acidic_and_correctly_labelled():
    # M5 (0.2 acetate / 0.05 carbon) is BICARBONATE-limited: residual pH is acidic.  The label bug the directive
    # flagged ("acid-limiting") is corrected; pin both the label text and the acidic pH.
    obj = json.loads(TABLE.read_text(), parse_constant=_reject)
    m5 = obj["rows"]["M5"]
    assert "BICARBONATE-LIMITED" in m5["desc"]
    assert m5["code_pH_davies"] < 5.0
    # M6 is the acid-limited mirror: less acidic than M5.
    assert obj["rows"]["M6"]["code_pH_davies"] > m5["code_pH_davies"]


def test_all_cases_present_and_decks_exist():
    obj = json.loads(CODE.read_text(), parse_constant=_reject)
    expected = {f"M{i}" for i in range(1, 12)}
    assert set(obj["cases"]) == expected
    for db in ("minteq.v4", "llnl"):
        for cid in expected:
            assert (BENCH / "inputs" / f"{db}_{cid}.pqi").exists(), f"missing deck {db}_{cid}.pqi"


def test_benchmark_obligation_is_external_validation_unavailable():
    ob = mixed_phreeqc_benchmark_obligation()
    assert ob.tool == "PHREEQC"
    assert ob.verdict == EXTERNAL_VALIDATION_UNAVAILABLE
    assert "minteq.v4" in ob.recipe["database"]
    assert ob.comparison is None   # no fabricated comparison
    assert "measured" in ob.recipe["independence_caveat"].lower()
