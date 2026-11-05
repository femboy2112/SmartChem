"""OPERATION XXI section 4 -- pins the THREE-comparator separation of the NIST SRM 191d comparison and its claim ledger.

The honest verdict the numbers give, no constant tuned:
  A  Table 1 (convention-INCLUSIVE)          -- WITHIN U = 0.010, but thinly (margin ~0.0011 pH).
  B  Table A1 (convention-MATCHED)           -- REFUTED, ~3x U_R.
  C  Table 1 with the model made SCALE-CONSISTENT (molar-K -> a_H transported to the molality scale)
                                             -- REFUTED even vs Table 1; the A pass survives ONLY under the molal-K
                                                reading.  So the measurement-level corroboration is contingent on an
                                                unresolved standard-state SCALE convention for K1/K2.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d import run_three_comparators_s4 as S4

REPO = Path(__file__).resolve().parents[3]
XXI_BASE = "774429e"   # the Operation XXI consolidation tip: carbonate_equilibrium.py must be byte-identical to it


@pytest.fixture(scope="module")
def res():
    return S4.evaluate()


def test_comparator_A_table1_is_within_U_but_thin(res):
    A = res["comparators"]["A_table1_certified_convention_inclusive"]
    assert A["passes"] is True
    assert A["comparison"]["within_U_over_interval"] is True
    # thin: the worst-case margin to the U edge is ~0.001 pH
    assert 0.0 < (A["comparison"]["U_pH"] - A["comparison"]["worst_abs_residual_pH"]) < 0.002


def test_comparator_B_tableA1_is_refuted(res):
    B = res["comparators"]["B_tableA1_noncertified_convention_matched"]
    assert B["passes"] is False
    assert B["comparison"]["within_U_over_interval"] is False
    assert B["comparison"]["abs_residual_over_U"] > 2.5           # ~3x U_R
    assert B["conclusion"]["refuted"] is not None and B["conclusion"]["corroborated"] is None


def test_comparator_C_scale_transport_refutes_even_table1_but_molal_reading_survives(res):
    C = res["comparators"]["C_table1_scale_transported"]
    assert C["passes"] is False                                   # under the molar-K label, OUTSIDE Table 1 U
    assert C["comparison"]["abs_residual_over_U"] > 1.0
    # ... yet the alternative molal-K reading DOES survive Table 1 -- that is the whole contingency
    assert C["alternative_molal_K_reading"]["within_table1_U"] is True
    assert "scale" in C["conclusion"]["decisive_next_measurement"].lower()


def test_the_scale_convention_is_what_flips_the_table1_verdict(res):
    """A and C use the SAME model prediction and the SAME Table-1 band (U=0.010); only the proton-activity SCALE
    differs.  A (mixed scale) is within U; C (scale-consistent, molar-K) is outside.  So the Table-1 'pass' is a
    convention artefact, not a robust physical agreement."""
    A = res["comparators"]["A_table1_certified_convention_inclusive"]
    C = res["comparators"]["C_table1_scale_transported"]
    assert A["comparison"]["U_pH"] == C["comparison"]["U_pH"] == 0.010
    assert A["comparison"]["within_U_over_interval"] is True
    assert C["comparison"]["within_U_over_interval"] is False


def test_overall_headline_is_not_a_robust_prediction(res):
    o = res["overall"]
    assert o["A_within_table1_U"] is True
    assert o["B_within_tableA1_U_R"] is False
    assert o["C_within_table1_U_under_molar_label"] is False
    assert o["C_within_table1_U_under_molal_reading"] is True
    assert o["no_constant_tuned"] is True
    assert "not" in o["headline"].lower() and "robust" in o["headline"].lower()


def test_no_model_constant_was_touched():
    out = subprocess.run(
        ["git", "diff", XXI_BASE, "--",
         "experiments/sandbox_foundation/carbonate_equilibrium.py",
         "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/run_measured.py",
         "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/result.json",
         "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/run_unit_convention_s5.py",
         "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/result_s5_unit_convention.json",
         "smartchem"],
        cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git unavailable or base SHA absent")
    assert out.stdout == ""                                       # XXI-4 only RE-FRAMES; it tunes/alters nothing


def test_result_is_strict_json(res):
    json.dumps(res, allow_nan=False)
