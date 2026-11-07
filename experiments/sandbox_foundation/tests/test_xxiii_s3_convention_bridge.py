"""OPERATION XXIII Phase III -- pins the convention-bridge result (PREREGISTRATION.md, CONVENTION_BRIDGE_VERDICT.md).

Recomputes the model side live (no PHREEQC needed) and checks it against the committed result JSON, so a silent change
to a constant, the activity law or the comparison algebra is caught.  No measured value is used to fit anything."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.sandbox_foundation.benchmarks.measured_buffers_xxiii import run_convention_bridge_xxiii as R

RESULT = Path(R.__file__).with_name("result_convention_bridge_xxiii.json")


@pytest.fixture(scope="module")
def frozen():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_instrument_gate_reproduces_the_repo_carbonate_solver():
    from experiments.sandbox_foundation import carbonate_equilibrium as C
    repo = C.solve(C.CarbonateWaterSystem(activity_model="davies", mode="closed", total_carbon_M=0.05, sodium_M=0.075))
    mine = R.carbonate_buffer(constants="repo_frozen_XIX", pairs=False).solve()
    assert abs(mine["pH_davies"] - repo.pH_activity) < 1e-9


@pytest.mark.parametrize("case,args", [
    ("carbonate_191d", None),
    ("phosphate_186g_equimolal", (0.025, 0.025)),
    ("phosphate_186g_physiological", (0.008695, 0.03043)),
])
def test_live_model_matches_the_frozen_result(frozen, case, args):
    m = (R.carbonate_buffer(constants="repo_frozen_XIX", pairs=False) if args is None
         else R.phosphate_buffer(*args, pairs=False)).solve()
    f = frozen["models"][case]["M0"]
    assert abs(m["p_aH_gCl"] - f["p_aH_gCl"]) < 1e-10
    c = R.compare(m, R.MEASURED[case], bg_ionic=m["ionic_strength"])
    assert abs(c["C2_residual"] - frozen["comparisons"][case]["M0"]["C2_residual"]) < 1e-10
    assert c["C2_equals_C3"]                                   # one test, not two passes


def test_the_measurement_level_negative_results_are_preserved(frozen):
    cmp_ = frozen["comparisons"]
    assert cmp_["carbonate_191d"]["M0"]["C1_within"] is True       # the thin Table 1 pass is kept ...
    assert cmp_["carbonate_191d"]["M0"]["C2_within"] is False      # ... and so is the measurement-level refutation
    assert cmp_["phosphate_186g_equimolal"]["M0"]["C1_within"] is False
    assert all(v == "MIXED/UNRESOLVED" for v in frozen["decision_rule"].values())
    assert frozen["no_constant_fitted"] is True


def test_scale_cannot_explain_the_carbonate_residual(frozen):
    # |log10 rho_w| <= 0.0018 for this solution (CONVENTION_BRIDGE_VERDICT.md section 1); the residual is ~6x larger.
    assert abs(frozen["comparisons"]["carbonate_191d"]["M0"]["C2_residual"]) > 5 * 0.0018


def test_a_single_pk2_shift_cannot_close_both_phosphate_formulations(frozen):
    r_e = frozen["comparisons"]["phosphate_186g_equimolal"]["M0"]["C2_residual"]
    r_p = frozen["comparisons"]["phosphate_186g_physiological"]["M0"]["C2_residual"]
    ur = (frozen["comparisons"]["phosphate_186g_equimolal"]["M0"]["C2_U_R"] ** 2
          + frozen["comparisons"]["phosphate_186g_physiological"]["M0"]["C2_U_R"] ** 2) ** 0.5
    assert abs(r_e - r_p) > 2 * ur                               # dpH/dpK2 ~ 1 for both, so the gap is composition-driven
