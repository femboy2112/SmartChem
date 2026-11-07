"""OPERATION XX section 5 -- pins the unit repair + convention-matched comparison for NIST SRM 191d.  Ooh yeah!
The verdict pinned here is the HONEST one the numbers gave: the Davies prediction survives the convention-INCLUSIVE
Table 1 U (thin margin) and is REFUTED against the convention-matched Table A1 U_R.  No constant was tuned."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d import run_unit_convention_s5 as S5

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def res():
    return S5.evaluate()


def test_certificate_comparators_are_the_ones_read_from_the_pdf():
    assert S5.CERT["table1_certified"]["pH_S_25C"] == 10.014 and S5.CERT["table1_certified"]["U"] == 0.010
    assert S5.CERT["tableA1_noncertified"]["pH_S_25C"] == 10.0137 and S5.CERT["tableA1_noncertified"]["U_R"] == 0.0029
    assert S5.CERT["tableA1_noncertified"]["includes_bates_guggenheim_convention_uncertainty"] is False
    assert S5.CERT["table1_certified"]["includes_bates_guggenheim_convention_uncertainty"] is True
    assert S5.SOLUTION_MASS_G == pytest.approx(1004.753)


def test_density_interval_and_its_derivation(res):
    lo, hi = res["density"]["interval_g_per_mL"]
    assert (lo, hi) == (1.0007, 1.0018)
    e_lo, e_hi = res["density"]["derived_edges_g_per_mL"]
    assert lo <= e_lo and e_hi <= hi                              # carried band contains the derived edges
    assert e_hi == pytest.approx(1004.753 / (1000.0 / 0.997047), rel=1e-6)    # phi_V_pair = 0 edge
    assert "0.997047" in res["density"]["source"] and "NOT measured" in res["density"]["source"]
    assert res["density"]["midpoint_g_per_mL"] == pytest.approx(1.00125)
    # the caller's heuristic 1.002-1.006 band is NOT inside the derived interval (honesty pin)
    assert 1.006 > hi


def test_molarity_conversion(res):
    for tag in ("lo", "mid", "hi"):
        row = res["corrected_davies"][tag]
        rho = row["rho_g_per_mL"]
        assert row["molarity_each_M"] == pytest.approx(0.025 * rho / 1.004753, rel=1e-6)   # 1004.7531 g exactly
        assert row["C_T_M"] == pytest.approx(2 * row["molarity_each_M"])
        assert row["Na_M"] == pytest.approx(3 * row["molarity_each_M"])
        assert row["molarity_each_M"] < 0.025                     # molarity is below molality (solute mass in the solution)
    assert res["corrected_davies"]["mid"]["molarity_each_M"] == pytest.approx(0.0249128, abs=1e-6)


def test_units_pH_shift_is_tiny_and_positive(res):
    v = res["verdict"]
    assert v["units_repair_shift_below_0p001"] is True
    lo, hi = v["units_repair_shift_pH_interval"]
    assert 0.0002 < lo <= hi < 0.0004                             # REFUTES the 'expected ~0.0001-0.0002': it is ~+0.0003
    assert res["xix_baseline_davies_pH_molality_fed_as_molarity"] == pytest.approx(10.0047926, abs=1e-6)


def test_residuals_and_honest_verdict(res):
    mid = res["corrected_davies"]["mid"]
    assert mid["pH"] == pytest.approx(10.0051020, abs=1e-6)
    assert mid["residual_vs_table1"] == pytest.approx(-0.0088980, abs=1e-6)
    assert mid["residual_vs_tableA1"] == pytest.approx(-0.0085980, abs=1e-6)
    v = res["verdict"]
    # Table 1 (convention-INCLUSIVE): within U over the WHOLE density interval, thin margin
    assert v["vs_table1_certified"]["within_U_over_whole_density_interval"] is True
    assert 0.0 < v["margin_to_table1_U_edge_pH"] < 0.0015
    # Table A1 (convention-MATCHED): REFUTED, at every density endpoint
    assert v["vs_tableA1_convention_matched"]["within_U_R_over_whole_density_interval"] is False
    assert v["vs_tableA1_convention_matched"]["status"].startswith("REFUTED")
    for tag in ("lo", "mid", "hi"):
        assert abs(res["corrected_davies"][tag]["residual_vs_tableA1"]) > 2.5 * 0.0029
        assert res["corrected_davies"][tag]["within_tableA1_U_R"] is False


def test_conclusion_is_not_hostage_to_the_density_band(res):
    for rho, blk in res["sensitivity_density_band"].items():
        assert blk["within_table1_U"] is True                     # incl. the caller's 1.002-1.006 heuristic band
        assert blk["within_tableA1_U_R"] is False


def test_scale_consistency_flag_is_recorded_and_fragile(res):
    f = res["verdict"]["scale_consistency_flag"]
    assert f["a_molar_K_with_aH_converted_to_molality_scale_within_table1_U"] is False   # pure-molar convention leaves U
    assert f["b_molal_K_molality_fed_within_table1_U"] is True
    for tag in ("lo", "mid", "hi"):
        assert not res["sensitivity_scale_consistency_NOT_headline"][tag][
            "a_molar_K_converted_to_molality_scale"]["within_tableA1_U_R"]


def test_common_mode_honesty_and_strict_json(res):
    json.dumps(res, allow_nan=False)
    assert "PARTIAL" in res["verdict"]["scope"] and "common-mode" in res["verdict"]["scope"]
    assert any("common-mode" in c for c in res["caveats"])


_XX5_MODEL_PATHS = ["experiments/sandbox_foundation/carbonate_equilibrium.py",
                    "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/run_measured.py",
                    "experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/result.json"]


def test_no_model_constant_was_touched():
    # XXIII: BOUNDED to XX-5's own range.  The original open-ended `git diff 0d2ab65 -- ... smartchem` compared a
    # historical base to the WORKING TREE, so the legitimate 1.6.0 smartchem/ release change tripped it (it only ever
    # passed in CI because the shallow checkout lacks 0d2ab65 and the test skipped).  The claim is historical: XX-5
    # (676bcfc) tuned nothing relative to its base 0d2ab65 -- a permanent fact once both commits exist.
    out = subprocess.run(["git", "diff", "0d2ab65", "676bcfc", "--", *_XX5_MODEL_PATHS, "smartchem"],
                         cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git unavailable or XX-5 commits absent (shallow clone)")
    assert out.stdout == ""


def test_carbonate_model_unchanged_since_xx5():
    """Forward guard (model files only; the production package is NOT in scope): any later edit of the carbonate model
    or its frozen comparison must be a conscious, reviewed change that updates this guard."""
    out = subprocess.run(["git", "diff", "676bcfc", "--", *_XX5_MODEL_PATHS], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git unavailable or 676bcfc absent (shallow clone)")
    assert out.stdout == ""
