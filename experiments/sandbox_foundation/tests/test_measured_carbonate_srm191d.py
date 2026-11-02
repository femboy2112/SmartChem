"""OPERATION XIX §4 -- the first MEASURED-validation rung: the repo carbonate solver, a BLIND prediction (no fitted
parameter), lands inside the NIST SRM 191d certified uncertainty band.  Pins the registered decision rule."""
from __future__ import annotations

import json

from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d.run_measured import (
    SRM191D,
    predict,
)


def test_certified_value_is_the_one_read_from_the_certificate():
    assert SRM191D["certified_pH_S_25C"] == 10.014
    assert SRM191D["U_k1_96"] == 0.010
    assert SRM191D["certificate_sha256"].startswith("ea316fb1")


def test_davies_blind_prediction_is_within_certified_U():
    res = predict()
    d = res["model"]["davies"]
    assert d["verdict"] == "SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL"
    assert d["within_certified_U"] is True                       # the registered CORROBORATED rule
    assert abs(d["residual_vs_certified"]) <= SRM191D["U_k1_96"]
    assert d["residual_vs_certified"] < 0.0                      # the model sits just below the certified value
    assert 0.09 < d["ionic_strength_M"] < 0.11                   # I ~ 0.1 as expected for this buffer


def test_ideal_model_misses_badly_so_the_activity_closure_matters():
    """A control: with NO activity correction the prediction is 0.3 pH off -- so the within-U hit is the Davies
    closure doing real work, not an accident of the buffer being near neutral."""
    res = predict()
    assert res["model"]["ideal"]["within_certified_U"] is False
    assert res["model"]["ideal"]["abs_residual"] > 0.2


def test_result_is_strict_json_and_labels_common_mode():
    res = predict()
    json.dumps(res, allow_nan=False)
    assert "common-mode" in res["headline"]["status"]
    assert any("common-mode" in c for c in res["caveats"])
