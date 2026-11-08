"""OPERATION XXV Phase III-B -- the holdout runner (holdout_guidone_xxv.py), exercised ONLY on SYNTHETIC
preregistrations whose states lie outside the reserved holdout region (T 313.15 K; pCO2 0.1-0.5 atm).  The measured
intervals here are FAKE numbers placed relative to the model's own prediction; they test the rule, not the model.

PASS = (1) a hash mismatch, malformed schema or model-digest drift refuses before any evaluation; (2) the interval rule
gives PASS / FAIL_HIGH / FAIL_LOW / AMBIGUOUS exactly as specified; (3) the FAIL_LOW rescue bisects the needed pCO2 at
the most-soluble corner and compares it to the ceiling; (4) mutated-source controls are run and judged; (5) the receipt
is strict JSON.
"""
from __future__ import annotations

import hashlib
import json
import math

import pytest

from experiments.sandbox_foundation import holdout_guidone_xxv as HR
from experiments.sandbox_foundation import open_calcite_xxv as OC
from experiments.sandbox_foundation.benchmarks.open_calcite_xxv.run_open_calcite_xxv import in_reserved_box

T_SYN = 313.15
P_GRID = [0.1]


@pytest.fixture(scope="module")
def ca_pred():
    assert not in_reserved_box(T_SYN, 0.1)
    return HR._evaluate(T_SYN, 0.0, 0.1, {}, OC.model_identity_digest())["Ca_total_M"]


def _prereg(tmp_path, meas, *, ceiling=0.1, controls=(), digest=None, shifts=(0.0,), **over):
    pr = {"schema": HR.PREREG_SCHEMA, "model_identity_digest": digest or OC.model_identity_digest(),
          "model_config": {}, "observable": "Ca_total_M", "measured_interval": list(meas),
          "state_grid": {"T_K": [T_SYN], "logKc_shift": list(shifts), "pCO2_atm": P_GRID},
          "verdict_rule": {"kind": HR.RULE_KIND, "fail_low_pco2_ceiling_atm": ceiling, "bisection_log10_tol": 0.05},
          "mutated_source_controls": list(controls), **over}
    for T in pr["state_grid"]["T_K"]:
        for p in pr["state_grid"]["pCO2_atm"] + [ceiling]:
            assert not in_reserved_box(T, p)
    path = tmp_path / "prereg.json"
    data = json.dumps(pr, sort_keys=True).encode()
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def test_interval_rule_unit():
    v = HR.interval_verdict
    assert v((1, 2), (2, 3)) == HR.PASS                       # closed intervals: touching overlaps
    assert v((3, 4), (1, 2)) == HR.FAIL_HIGH
    assert v((1, 2), (3, 4), needed_pco2=math.inf, ceiling=0.1) == HR.FAIL_LOW
    assert v((1, 2), (3, 4), needed_pco2=0.05, ceiling=0.1) == HR.AMBIGUOUS
    assert v((1, 2), (3, 4), needed_pco2=None, ceiling=0.1) == HR.AMBIGUOUS


def test_refusals_happen_before_evaluation(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("model evaluated despite a refusal")
    monkeypatch.setattr(HR, "_evaluate", boom)
    path, sha = _prereg(tmp_path, (0.001, 0.002))
    with pytest.raises(HR.PreregistrationError, match="sha256"):
        HR.run_holdout(path, "0" * 64, tmp_path / "r.json")
    path2, sha2 = _prereg(tmp_path, (0.001, 0.002), digest="f" * 64)
    with pytest.raises(HR.PreregistrationError, match="drift"):
        HR.run_holdout(path2, sha2, tmp_path / "r.json")
    path3, sha3 = _prereg(tmp_path, (0.002, 0.001))
    with pytest.raises(HR.PreregistrationError, match="measured_interval"):
        HR.run_holdout(path3, sha3, tmp_path / "r.json")
    path4, sha4 = _prereg(tmp_path, (0.001, 0.002), observable="pH_activity")
    with pytest.raises(HR.PreregistrationError, match="observable"):
        HR.run_holdout(path4, sha4, tmp_path / "r.json")
    assert not (tmp_path / "r.json").exists()


def _strict_load(p):
    def bad(x):
        raise AssertionError(f"non-finite token {x}")
    return json.loads(p.read_text(), parse_constant=bad)


def test_pass_and_fail_high_with_a_discriminating_control(tmp_path, ca_pred):
    path, sha = _prereg(tmp_path, (0.98 * ca_pred, 1.02 * ca_pred),
                        controls=[{"name": "logKc +0.30", "logKc_shift": 0.30, "expected_verdict": "FAIL_HIGH"}])
    r = HR.run_holdout(path, sha, tmp_path / "receipt.json")
    assert r["verdict"] == HR.PASS
    c = r["controls"][0]
    assert c["verdict"] == HR.FAIL_HIGH and c["as_expected"] and c["differs_from_main"]
    assert r["controls_all_as_expected"] is True
    on_disk = _strict_load(tmp_path / "receipt.json")
    assert on_disk["preregistration_sha256"] == sha and on_disk["model_identity_digest"] == OC.model_identity_digest()
    path2, sha2 = _prereg(tmp_path, (0.5 * ca_pred, 0.9 * ca_pred))
    assert HR.run_holdout(path2, sha2, tmp_path / "r2.json")["verdict"] == HR.FAIL_HIGH


def test_fail_low_when_the_ceiling_is_at_the_grid_top(tmp_path, ca_pred):
    path, sha = _prereg(tmp_path, (1.5 * ca_pred, 2.0 * ca_pred), ceiling=0.1)
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.FAIL_LOW and r["rescue"]["status"] == "CEILING_AT_OR_BELOW_GRID_TOP"
    assert _strict_load(tmp_path / "r.json")["rescue"]["needed_pco2_atm"] == "EXCEEDS_CEILING"


def test_fail_low_vs_ambiguous_by_the_bisected_pco2(tmp_path, ca_pred):
    # ~10% above the 0.1 atm prediction: with Ca ~ pCO2^(1/3) the model needs ~0.13 atm
    path, sha = _prereg(tmp_path, (1.10 * ca_pred, 1.20 * ca_pred), ceiling=0.5)
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.AMBIGUOUS and r["rescue"]["status"] == "NEEDED_AT_OR_BELOW_CEILING"
    need = r["rescue"]["needed_pco2_atm"]
    assert 0.1 < need <= 0.5
    lo, hi = r["rescue"]["bracket_atm"]
    assert HR._evaluate(T_SYN, 0.0, lo, {}, OC.model_identity_digest())["Ca_total_M"] < 1.10 * ca_pred
    assert HR._evaluate(T_SYN, 0.0, hi, {}, OC.model_identity_digest())["Ca_total_M"] >= 1.10 * ca_pred
    # the same shortfall under a ceiling the model cannot reach it by -> FAIL_LOW
    path2, sha2 = _prereg(tmp_path, (1.10 * ca_pred, 1.20 * ca_pred), ceiling=0.12)
    r2 = HR.run_holdout(path2, sha2, tmp_path / "r2.json")
    assert r2["verdict"] == HR.FAIL_LOW and r2["rescue"]["status"] == "NEEDED_EXCEEDS_CEILING"
    assert r2["rescue"]["value_at_ceiling"] < 1.10 * ca_pred


def test_model_refusal_at_the_ceiling_is_ambiguous_not_fail(tmp_path, ca_pred):
    path, sha = _prereg(tmp_path, (1.5 * ca_pred, 2.0 * ca_pred), ceiling=2.0)    # > 1 atm: the model refuses
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.AMBIGUOUS and r["rescue"]["status"].startswith("MODEL_REFUSED_AT_CEILING")
