"""OPERATION XIII P5 -- the headless flagship demo (strict frames, honest scenario matrix, no fabricated success)."""
from __future__ import annotations

import json

import pytest

from experiments.sandbox_foundation import vinegar_bicarbonate_demo as demo


@pytest.fixture(scope="module")
def report():
    return demo.run_pack()


def test_report_is_strict_json(report):
    text = json.dumps(report, allow_nan=False)
    for tok in ("NaN", "Infinity", "-Infinity"):
        assert tok not in text


def test_scenario_matrix_is_honest(report):
    m = report["scenario_matrix"]
    for sid in ("B1", "B2", "B3", "B4", "B5", "B6"):
        assert m[sid] == demo.NUMERICALLY_VERIFIED, (sid, m[sid])
    # the unsupported scenarios are DEFERRED, never a fabricated success.
    assert m["B7"] == demo.DEFERRED and m["B8"] == demo.DEFERRED
    assert report["honesty"]["deferred"] == ["B7", "B8"]


def test_every_frame_satisfies_the_renderer_contract(report):
    n = 0
    for sc in report["scenarios"]:
        for fr in sc["frames"]:
            problems = demo.validate_vinegar_frame(fr)
            assert not problems, (sc["scenario"], problems)
            n += 1
    assert n >= 7   # B1..B4 (4) + B5 (2) + B6 (2)


def test_unsupported_quantities_are_null_never_zero(report):
    for sc in report["scenarios"]:
        for fr in sc["frames"]:
            for nm, q in fr["unsupported"].items():
                assert q["value"] is None, (nm, q)
                assert q["kind"] == "UNSUPPORTED"


def test_nothing_claims_benchmark_calibration_or_measurement(report):
    for sc in report["scenarios"]:
        for fr in sc["frames"]:
            t = fr["trust"]
            assert t["observed_measurement"] is False
            assert t["benchmarked_against_reference_solver"] is False
            assert t["calibrated_to_measurement"] is False


def test_control_pH_anchors(report):
    byid = {sc["scenario"]: sc for sc in report["scenarios"]}
    b1 = byid["B1"]["frames"][0]["pH"]["value"]
    b2 = byid["B2"]["frames"][0]["pH"]["value"]
    b3 = byid["B3"]["frames"][0]["pH"]["value"]
    assert abs(b1 - 7.0) < 1e-6         # water
    assert 2.8 < b2 < 3.0               # 0.1 M acetic acid
    assert 8.0 < b3 < 8.4               # 0.1 M NaHCO3 buffer


def test_B5_bicarbonate_limited_is_acidic_and_below_acid_limited():
    sc = demo.run_scenario("B5")
    acid_lim = sc.frames[0]["pH"]["value"]     # excess bicarbonate
    bicarb_lim = sc.frames[1]["pH"]["value"]   # excess acid -> acidic
    assert bicarb_lim < 5.0
    assert bicarb_lim < acid_lim
    assert "mislabel" in sc.note


def test_B6_open_and_sealed_differ_and_dynamics_conserve_and_relax():
    sc = demo.run_scenario("B6")
    op = sc.frames[0]["pH"]["value"]
    se = sc.frames[1]["pH"]["value"]
    assert abs(op - se) > 0.1
    ts = sc.time_series
    assert len(ts) >= 10
    for s in ts:
        assert abs(s["carbon_residual_mol"]) < 1e-12        # carbon conserved every sample
    assert abs(ts[-1]["flux_mol_per_s"]) < abs(ts[0]["flux_mol_per_s"])   # flux relaxes


def test_deferred_scenarios_carry_no_frames_or_time_series():
    for sid in ("B7", "B8"):
        sc = demo.run_scenario(sid)
        assert sc.status == demo.DEFERRED
        assert sc.frames == () and sc.time_series == ()


def test_closed_status_is_earned_and_demotes_on_unverified():
    # a verdict carrying UNVERIFIED must yield FAILED, never a free NUMERICALLY_VERIFIED.
    assert demo._closed_status(0.1, 0.1, 0.1, "davies", "NUMERICALLY_UNVERIFIED") == demo.FAILED
    assert demo._closed_status(0.1, 0.1, 0.1, "davies", "SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL") == demo.NUMERICALLY_VERIFIED


def test_model_source_digest_is_deterministic():
    assert demo.model_source_digest()["sha256"] == demo.model_source_digest()["sha256"]
    assert len(demo.model_source_digest()["sha256"]) == 64


def test_main_single_scenario_and_csv(tmp_path):
    jf, cf = tmp_path / "r.json", tmp_path / "r.csv"
    rc = demo.main(["--scenario", "B6", "--json", str(jf), "--csv", str(cf)])
    assert rc == 0
    obj = json.loads(jf.read_text())
    assert obj["scenario_matrix"] == {"B6": demo.NUMERICALLY_VERIFIED}
    csv = cf.read_text().splitlines()
    assert csv[0].startswith("scenario,time_s,pH")
    assert len(csv) > 10 and csv[1].startswith("B6,")
