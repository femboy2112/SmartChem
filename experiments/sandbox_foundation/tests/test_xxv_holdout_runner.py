"""OPERATION XXV Phase III-B -- the holdout runner (holdout_guidone_xxv.py), exercised ONLY on SYNTHETIC
preregistrations whose states lie outside the reserved holdout region (every T is 313.15 / 318.15 / 370 K, so no pCO2 the
rule can reach -- grid, ceiling or bisection -- lands in the box).  The measured values come from SYNTHETIC
transcriptions placed relative to the model's own prediction; they test the instrument, not the model.  A module-wide
guard (the reviewer's guard.py pattern) ends the session if anything asks the model for a reserved-box state.

Each test names the XXV runner-review finding it pins (D1..D10).  Most logic tests replace the model evaluation with a
deterministic stand-in (``_fake``) so they exercise the RUNNER; the end-to-end tests use the real model.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import textwrap

import pytest

from experiments.sandbox_foundation import holdout_guidone_xxv as HR
from experiments.sandbox_foundation import open_calcite_xxv as OC
from experiments.sandbox_foundation.benchmarks.open_calcite_xxv.run_open_calcite_xxv import (
    RESERVED_T_K,
    in_reserved_box,
)

T_SYN = 313.15
P_GRID = [0.1, 0.105]
REPO = HR.REPO
PY = sys.executable
GUIDONE = REPO / "experiments/sandbox_foundation/holdouts/guidone2025_table1_transcription.json"
GUIDONE_SHA = "9f33b5407bf775bc4cf18afbf43961fb9e1011e45796fca2c51f5ac912a819ea"      # prereg section 1
EXAMPLE = REPO / "experiments/sandbox_foundation/holdouts/EXAMPLE_PREREG_SCHEMA_xxv.json"


# --------------------------------------------------------------------------------------------- reserved-box guard
def _guard(T, p):
    if in_reserved_box(float(T), float(p)):
        pytest.exit(f"GUARD: reserved-box state ({T}, {p}) requested -- aborting the session", returncode=99)


@pytest.fixture(scope="module", autouse=True)
def reserved_box_guard():
    build, asm = OC.build_open_calcite_world, OC.assemble_open_calcite_world

    def g_build(T, p, **kw):
        _guard(T, p)
        return build(T, p, **kw)

    def g_asm(T, p, **kw):
        _guard(T, p)
        return asm(T, p, **kw)

    mp = pytest.MonkeyPatch()
    mp.setattr(OC, "build_open_calcite_world", g_build)
    mp.setattr(OC, "assemble_open_calcite_world", g_asm)
    yield
    mp.undo()


@pytest.fixture(scope="module")
def ident():
    return HR.identities(HR.closure_bytes(), {})


@pytest.fixture(scope="module")
def ca_pred(ident):
    return HR._evaluate(T_SYN, 0.0, 0.1, {}, ident["model_identity_digest"])["Ca_total_M"]


# --------------------------------------------------------------------------------------------- builders
def _transcription(tmp_path, value, u, *, name="transcription.json", extra=None):
    tr = {"schema": HR.TRANSCRIPTION_SCHEMA, "note": "SYNTHETIC (test only)",
          "measured": {"Ca_tot_M": {"value": value, "u_2sigma": u}, **(extra or {})}}
    path = tmp_path / name
    data = json.dumps(tr).encode()
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def _controls(T=T_SYN, p=0.1):
    return [{"name": "C1", "kind": HR.LOGKC_SHIFT, "logKc_shift": 0.60, "expected": "FAIL_HIGH"},
            {"name": "C2", "kind": HR.LOGKC_SHIFT, "logKc_shift": -1.50, "expected": "FAIL_LOW"},
            {"name": "C3", "kind": HR.OFF_TEMPERATURE_CONSTANT, "T_K": T, "pCO2_atm": p, "slots": list(HR.OFF_T_SLOTS),
             "expected": "REFUSED"},
            {"name": "C4", "kind": HR.OUT_OF_DOMAIN_TEMPERATURE, "T_K": 370.0, "pCO2_atm": p, "expected": "REFUSED"}]


def _pr_dict(ident, tr_path, tr_sha, *, ceiling=0.5, T=(T_SYN,), shifts=(0.0,), p=tuple(P_GRID), controls=None):
    t_mid = sorted(T)[len(T) // 2]
    return {"schema": HR.PREREG_SCHEMA, "holdout_id": "synthetic-test", "note": "SYNTHETIC, out of the reserved box",
            "runner_sha256": ident["runner_sha256"], "model_identity_digest": ident["model_identity_digest"],
            "model_config": {}, "observable": "Ca_total_M",
            "measured": {"transcription_path": str(tr_path), "transcription_sha256": tr_sha, "quantity": "Ca_tot_M"},
            "state_grid": {"T_K": list(T), "logKc_shift": list(shifts), "pCO2_atm": list(p)},
            "verdict_rule": {"kind": HR.RULE_KIND, **HR.RULE_TOKENS, "fail_low_pco2_ceiling_atm": ceiling,
                             "rescue_corner": {"T_K": min(T), "logKc_shift": max(shifts)},
                             "bisection_log10_tol": 0.05},
            "mandatory_control_kinds": list(HR.CONTROL_KINDS),
            "controls": _controls(T=t_mid) if controls is None else controls,
            "informational_point": {"T_K": t_mid, "pCO2_atm": max(p), "logKc_shift": 0.0}}


def _assert_out_of_box(pr):
    """Every temperature the run can touch lies outside the reserved T range, so NO pCO2 (grid, ceiling, bisection)
    can produce a reserved-box state."""
    temps = (pr["state_grid"]["T_K"] + [c["T_K"] for c in pr["controls"] if "T_K" in c]
             + [pr["verdict_rule"]["rescue_corner"]["T_K"], pr["informational_point"]["T_K"]])
    for T in temps:
        assert not (RESERVED_T_K[0] <= T <= RESERVED_T_K[1]), T


def _write_pr(tmp_path, pr, *, raw=None, name="prereg.json"):
    _assert_out_of_box(pr)
    data = raw if raw is not None else json.dumps(pr, sort_keys=True).encode()
    path = tmp_path / name
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def _prereg(tmp_path, ident, value, u, **kw):
    tr, tsha = _transcription(tmp_path, value, u)
    return _write_pr(tmp_path, _pr_dict(ident, tr, tsha, **kw))


def _strict_load(p):
    def bad(x):
        raise AssertionError(f"non-finite token {x}")
    return json.loads(p.read_text(), parse_constant=bad)


def _floats(obj) -> set:
    """Every float anywhere in a JSON-like object (an exact-equality search, not a substring one)."""
    if isinstance(obj, dict):
        return set().union(*(_floats(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(_floats(v) for v in obj)) if obj else set()
    return {obj} if isinstance(obj, float) else set()


def _main_grid_values(T=(T_SYN,), shifts=(0.0,)) -> set:
    return {_fake_value(t, s, p) for t in T for s in shifts for p in P_GRID}


def _fake_value(T, s, p):
    """A deterministic stand-in obeying the declared premise (up with pCO2 and Kc, down with T)."""
    return 1.0123e-3 * 10 ** (s / 3.0) * (p / 0.1) ** 0.32 * (1.0 - 0.016 * (T - T_SYN))


def _fake(calls, value=_fake_value):
    def ev(T, s, p, cfg, mid):
        calls.append((float(T), float(s), float(p)))
        _guard(T, p)
        v = value(float(T), float(s), float(p))
        return {"T_K": T, "logKc_shift": s, "pCO2_atm": p, "Ca_total_M": v, "DIC_M": 3 * v, "HCO3_plus_CO3_M": 2 * v,
                "pH_activity": 7.0, "run_identity_digest": "fake"}
    return ev


# --------------------------------------------------------------------------------------------- the rule
def test_interval_rule_unit():
    v = HR.interval_verdict
    assert v((1, 2), (2, 3)) == HR.PASS                       # closed intervals: touching overlaps (inclusive PASS)
    assert v((2, 3), (1, 2)) == HR.PASS
    assert v((3, 4), (1, 2)) == HR.FAIL_HIGH
    assert v((1, 2), (3, 4), needed_pco2=math.inf, ceiling=0.1) == HR.FAIL_LOW
    assert v((1, 2), (3, 4), needed_pco2=0.1, ceiling=0.1) == HR.AMBIGUOUS        # strict: needed == ceiling
    assert v((1, 2), (3, 4), needed_pco2=0.05, ceiling=0.1) == HR.AMBIGUOUS
    assert v((1, 2), (3, 4), needed_pco2=None, ceiling=0.1) == HR.AMBIGUOUS


# --------------------------------------------------------------------------------------------- D1: INVALID, controls first
def test_D1_no_controls_or_a_missing_mandatory_kind_is_refused_at_load(tmp_path, ident, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("model evaluated despite a refusal")
    monkeypatch.setattr(HR, "_evaluate", boom)
    tr, tsha = _transcription(tmp_path, 1e-3, 1e-5)
    base = _pr_dict(ident, tr, tsha)
    cases = {
        "no controls": dict(base, controls=[]),
        "no C3 kind": dict(base, controls=[c for c in base["controls"] if c["kind"] != HR.OFF_TEMPERATURE_CONSTANT]),
        "no C4 kind": dict(base, controls=[c for c in base["controls"] if c["kind"] != HR.OUT_OF_DOMAIN_TEMPERATURE]),
        "mandatory list short": dict(base, mandatory_control_kinds=[HR.LOGKC_SHIFT]),
        "no FAIL_LOW control": dict(base, controls=[c for c in base["controls"] if c["name"] != "C2"]),
        "no mandatory list": {k: v for k, v in base.items() if k != "mandatory_control_kinds"},
        "old control shape": dict(base, controls=[{"name": "C1", "logKc_shift": 0.6, "expected_verdict": "FAIL_HIGH"}]),
        "C3 short of slots": dict(base, controls=base["controls"][:2] + [dict(base["controls"][2], slots=["Kc_calcite"])]
                                  + base["controls"][3:]),
        "C3 off the nominal T": dict(base, state_grid=dict(base["state_grid"], T_K=[T_SYN, 318.15, 323.15])),
    }
    for label, pr in cases.items():
        path, sha = _write_pr(tmp_path, pr)
        with pytest.raises(HR.PreregistrationError):
            HR.run_holdout(path, sha, tmp_path / "r.json")
        assert not (tmp_path / "r.json").exists(), label


def test_D1_a_misbehaving_control_is_INVALID_and_the_main_grid_is_never_evaluated(tmp_path, ident, monkeypatch):
    calls = []
    monkeypatch.setattr(HR, "_evaluate", _fake(calls))
    main_ca = _fake_value(T_SYN, 0.0, 0.1)
    ctr = _controls() + [{"name": "C5 too small", "kind": HR.LOGKC_SHIFT, "logKc_shift": 0.001,
                          "expected": "FAIL_HIGH"}]                         # +0.001 cannot FAIL_HIGH: it misbehaves
    tr, tsha = _transcription(tmp_path, 1.003 * main_ca, 0.02 * main_ca)
    path, sha = _write_pr(tmp_path, _pr_dict(ident, tr, tsha, controls=ctr))
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.INVALID and r["controls_all_as_expected"] is False
    assert r["invalid_reasons"] == ["CONTROL_MISBEHAVED: ['C5 too small']"]
    assert [c["as_expected"] for c in r["controls"]] == [True, True, True, True, False]
    assert calls and all(s != 0.0 for _, s, _ in calls), "a main-grid state was evaluated"
    for key in ("prediction_interval", "evaluations", "rescue", "informational", "monotonicity"):
        assert key not in r
    assert not _floats(_strict_load(tmp_path / "r.json")) & _main_grid_values()
    out = HR.stdout_summary(r)
    assert out["verdict"] == HR.INVALID and "prediction_interval" not in out
    assert not _floats(out) & _main_grid_values()


def test_D1_D3_a_reintroduced_untagged_constant_makes_the_instrument_misbehave(ident, monkeypatch):
    # put defect 3 back (no tag check): C3 must stop being refused, so the run could only be INVALID
    monkeypatch.setattr(OC, "require_constants_at", lambda T, tagged: None)
    res = HR.run_control(_controls()[2], "Ca_total_M", None, None, None, {}, ident["model_identity_digest"])
    assert res["as_expected"] is False and res["outcome"] == "MISBEHAVED"
    davies = next(r for r in res["per_slot"] if r["slot"] == OC.DAVIES_A_SLOT)
    assert davies["outcome"] == "NOT_REFUSED"                                # the reviewer's -0.53 % injection


# --------------------------------------------------------------------------------------------- D2: typed control kinds
def test_D2_logKc_control_shift_is_added_to_every_grid_point(monkeypatch):
    calls = []
    monkeypatch.setattr(HR, "_evaluate", _fake(calls))
    grid = {"T_K": [T_SYN, 318.15], "logKc_shift": [-0.02, 0.0, 0.02], "pCO2_atm": P_GRID}
    rule = {"fail_low_pco2_ceiling_atm": 0.5, "bisection_log10_tol": 0.05,
            "rescue_corner": {"T_K": T_SYN, "logKc_shift": 0.02}}
    meas = (_fake_value(T_SYN, 0.0, 0.1) * 0.98, _fake_value(T_SYN, 0.0, 0.1) * 1.02)
    res = HR.run_control({"name": "C1", "kind": HR.LOGKC_SHIFT, "logKc_shift": 0.6, "expected": "FAIL_HIGH"},
                         "Ca_total_M", grid, meas, rule, {}, "mid")
    assert res["as_expected"] and res["outcome"] == HR.FAIL_HIGH
    seen = {(T, round(s, 12), p) for T, s, p in calls}
    want = {(T, round(s + 0.6, 12), p) for T in grid["T_K"] for s in grid["logKc_shift"] for p in grid["pCO2_atm"]}
    assert seen == want                                                      # every grid point, shifted, nothing else
    res2 = HR.run_control({"name": "C2", "kind": HR.LOGKC_SHIFT, "logKc_shift": -1.5, "expected": "FAIL_LOW"},
                          "Ca_total_M", grid, meas, rule, {}, "mid")
    assert res2["as_expected"] and res2["outcome"] == HR.FAIL_LOW
    assert res2["rescue"]["corner"] == {"T_K": T_SYN, "logKc_shift": pytest.approx(0.02 - 1.5)}


def test_D2_D3_off_temperature_constants_are_each_refused_and_the_seam_discriminates(ident):
    res = HR.run_control(_controls()[2], "Ca_total_M", None, None, None, {}, ident["model_identity_digest"])
    assert res["as_expected"] is True and res["outcome"] == HR.REFUSED
    rows = {r["slot"]: r for r in res["per_slot"]}
    assert set(rows) == set(HR.OFF_T_SLOTS) == {"Kc_calcite", "K HCO3- formation", "K CO2(aq) formation",
                                                 "K water formation", "KH_CO2", "davies_A", "rho_w"}
    for slot, r in rows.items():
        assert r["injected"]["T_K"] == 298.15, slot
        assert r["refused"] and r["error"]["type"] == "OffTemperatureConstantError", (slot, r)
        assert r["seam_accepts_at_T_constant"] is True, slot                # the refusal is the temperature's


def test_D2_out_of_domain_temperature_is_refused_and_recorded(tmp_path, ident):
    res = HR.run_control(_controls()[3], "Ca_total_M", None, None, None, {}, ident["model_identity_digest"])
    assert res["as_expected"] and res["outcome"] == HR.REFUSED
    assert res["error"]["type"] == "TemperatureLawDomainError" and res["T_K"] == 370.0
    tr, tsha = _transcription(tmp_path, 1e-3, 1e-5)
    pr = _pr_dict(ident, tr, tsha)
    pr["controls"][3] = dict(pr["controls"][3], T_K=330.0)                  # inside the law: tests nothing
    path, sha = _write_pr(tmp_path, pr)
    with pytest.raises(HR.PreregistrationError, match="INSIDE"):
        HR.load_preregistration(path, sha)


# --------------------------------------------------------------------------------------------- D4: strict JSON, transcription
def test_D4_duplicate_unknown_and_nonfinite_keys_are_refused(tmp_path, ident):
    tr, tsha = _transcription(tmp_path, 1e-3, 1e-5)
    pr = _pr_dict(ident, tr, tsha)
    good = json.dumps(pr)
    path, sha = _write_pr(tmp_path, pr, raw=good.encode())
    HR.load_preregistration(path, sha)                                      # control: the clean bytes load
    dup_top = good[:-1] + ', "holdout_id": "other"}'
    dup_nested = good.replace('"T_K": [313.15]', '"T_K": [313.15], "T_K": [323.15]', 1)
    assert dup_nested != good
    unknown_top = json.dumps(dict(pr, measured_interval=[1e-3, 2e-3]))      # the old way of stating M
    unknown_nested = json.dumps(dict(pr, verdict_rule=dict(pr["verdict_rule"], margin=0.1)))
    nan = good.replace('"bisection_log10_tol": 0.05', '"bisection_log10_tol": NaN')
    assert nan != good
    for label, raw in (("dup top", dup_top), ("dup nested", dup_nested), ("unknown top", unknown_top),
                       ("unknown nested", unknown_nested), ("NaN", nan)):
        p2, s2 = _write_pr(tmp_path, pr, raw=raw.encode(), name="bad.json")
        with pytest.raises(HR.PreregistrationError):
            HR.load_preregistration(p2, s2)


def test_D4_the_measured_interval_is_computed_from_the_sha_pinned_transcription(tmp_path, ident):
    tr, tsha = _transcription(tmp_path, 2.0e-3, 0.1e-3)
    path, sha = _write_pr(tmp_path, _pr_dict(ident, tr, tsha))
    _, _, m = HR.load_preregistration(path, sha)
    assert m["interval"] == [2.0e-3 - 0.1e-3, 2.0e-3 + 0.1e-3] and m["transcription_sha256"] == tsha
    tr.write_bytes(tr.read_bytes().replace(b"0.002", b"0.003"))             # the transcription moves after pinning
    with pytest.raises(HR.PreregistrationError, match="transcription sha256"):
        HR.load_preregistration(path, sha)


def test_D4_the_frozen_guidone_transcription_gives_the_registered_interval():
    # reads measured numbers only; no model evaluation of any kind
    m = HR.measured_from_transcription(GUIDONE, GUIDONE_SHA, "Ca_tot_M")
    assert m["interval"] == pytest.approx([5.52e-4, 6.06e-4], rel=1e-12)    # prereg section 1: M
    assert m["informational_quantities"]["C_tot_M"] == {"value": 1.21e-3, "u_2sigma": 0.10e-3}
    with pytest.raises(HR.PreregistrationError):
        HR.measured_from_transcription(GUIDONE, "0" * 64, "Ca_tot_M")


# --------------------------------------------------------------------------------------------- D5: identity pins
def test_D5_runner_and_model_pins_are_checked_before_any_evaluation(tmp_path, ident, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("model evaluated despite a refusal")
    monkeypatch.setattr(HR, "_evaluate", boom)
    monkeypatch.setattr(OC, "build_open_calcite_world", boom)
    monkeypatch.setattr(OC, "assemble_open_calcite_world", boom)
    tr, tsha = _transcription(tmp_path, 1e-3, 1e-5)
    pr = _pr_dict(ident, tr, tsha)
    for field, match in (("runner_sha256", "runner_sha256 drift"), ("model_identity_digest", "digest drift")):
        path, sha = _write_pr(tmp_path, dict(pr, **{field: "f" * 64}))
        with pytest.raises(HR.PreregistrationError, match=match):
            HR.run_holdout(path, sha, tmp_path / "r.json")
    path, sha = _write_pr(tmp_path, pr)
    with pytest.raises(HR.PreregistrationError, match="sha256"):
        HR.run_holdout(path, "0" * 64, tmp_path / "r.json")
    assert not (tmp_path / "r.json").exists()


def test_D5_identities_come_from_one_read_and_cover_every_runner_byte(ident):
    code = HR.closure_bytes()
    assert set(code) == set(OC.code_closure()) | {HR.RUNNER_MODULE}
    assert ident["runner_sha256"] == hashlib.sha256(open(HR.__file__, "rb").read()).hexdigest()
    assert ident["model_identity_digest"] == OC.model_identity_digest()
    with pytest.raises(OC.OpenCalciteError):
        OC.model_identity_digest_for_code({"x": "0" * 64})


# --------------------------------------------------------------------------------------------- D7: premise
def test_D7_a_flat_pco2_response_is_INVALID_not_a_verdict(tmp_path, ident, monkeypatch):
    def flat_at_one_pair(T, s, p):
        return _fake_value(T, s, 0.1) if (T, s) == (318.15, 0.0) else _fake_value(T, s, p)   # dCa/dpCO2 == 0 there
    monkeypatch.setattr(HR, "_evaluate", _fake([], flat_at_one_pair))
    v = _fake_value(T_SYN, 0.0, 0.1)
    tr, tsha = _transcription(tmp_path, 1.003 * v, 0.02 * v)
    path, sha = _write_pr(tmp_path, _pr_dict(ident, tr, tsha, T=(T_SYN, 318.15)))
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.INVALID and r["controls_all_as_expected"] is True
    assert r["premise_violations"] == [{"T_K": 318.15, "logKc_shift": 0.0}]
    assert "prediction_interval" not in r
    assert not _floats(_strict_load(tmp_path / "r.json")) & _main_grid_values(T=(T_SYN, 318.15))

    def flat_when_shifted_up(T, s, p):                                       # the same failure inside a control
        return _fake_value(T, s, 0.1) if s > 0.5 else _fake_value(T, s, p)
    monkeypatch.setattr(HR, "_evaluate", _fake([], flat_when_shifted_up))
    r2 = HR.run_holdout(path, sha, tmp_path / "r2.json")
    assert r2["verdict"] == HR.INVALID and r2["invalid_reasons"] == ["CONTROL_MISBEHAVED: ['C1']"]
    assert r2["controls"][0]["outcome"] == "PREMISE_VIOLATED"


# --------------------------------------------------------------------------------------------- D10: fixed corner
def test_D10_the_rescue_corner_is_the_declared_fixed_corner(tmp_path, ident, monkeypatch):
    calls = []
    monkeypatch.setattr(HR, "_evaluate", _fake(calls))
    v = _fake_value(T_SYN, 0.02, 0.105)                                      # = max(P)
    tr, tsha = _transcription(tmp_path, 1.15 * v, 0.05 * v)                 # just above P: the rescue must run
    pr = _pr_dict(ident, tr, tsha, T=(T_SYN, 318.15), shifts=(-0.02, 0.0, 0.02))
    path, sha = _write_pr(tmp_path, pr)
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.AMBIGUOUS, r.get("invalid_reasons")
    assert r["rescue"]["corner"] == {"T_K": T_SYN, "logKc_shift": 0.02}
    assert r["rescue"]["bisection_log10_tol"] == 0.05 and r["rescue"]["status"] == "NEEDED_AT_OR_BELOW_CEILING"
    above_grid = {(T, round(s, 12)) for T, s, p in calls if p > max(P_GRID)}
    assert above_grid == {(T_SYN, 0.02), (T_SYN, round(0.02 - 1.5, 12))}    # main corner, C2's shifted corner
    for bad in ({"T_K": 318.15, "logKc_shift": 0.02}, {"T_K": T_SYN, "logKc_shift": 0.0}):
        p2, s2 = _write_pr(tmp_path, dict(pr, verdict_rule=dict(pr["verdict_rule"], rescue_corner=bad)), name="b.json")
        with pytest.raises(HR.PreregistrationError, match="rescue_corner"):
            HR.load_preregistration(p2, s2)


# --------------------------------------------------------------------------------------------- D8: statements
def test_D8_receipt_statements_are_exact_and_the_constants_claim_is_correct(tmp_path, ident, monkeypatch):
    monkeypatch.setattr(HR, "_evaluate", _fake([]))
    v = _fake_value(T_SYN, 0.0, 0.1)
    tr, tsha = _transcription(tmp_path, v, 0.02 * v, extra={"C_tot_M": {"value": 2.1 * v, "u_2sigma": 0.1 * v},
                                                             "pH": {"value": 7.1, "u_2sigma": 0.1}})
    path, sha = _write_pr(tmp_path, _pr_dict(ident, tr, tsha))
    r = HR.run_holdout(path, sha, tmp_path / "r.json")
    assert r["verdict"] == HR.PASS
    assert r["uncertainty_statement"] == ("P is a lower bound on the model's own uncertainty (K_H, K1, K2 "
                                          "uncertainties unstated, not propagated)")
    assert r["tier"] == "W (weak, nuisance-limited): cannot by itself satisfy the 2.0-alpha gate"
    assert "biased high by about 15% or low by about 40%" in r["power_statement"]
    claim = r["constants_claim"]
    assert "all P&B" not in claim and "constants are P&B" not in claim
    for must in ("Plummer & Busenberg (1982)", "Kw: the phreeqc.dat", "NOT Plummer & Busenberg", "0.509",
                 "Malmberg & Maryott", "Kell"):
        assert must in claim, must
    asm = OC.assemble_open_calcite_world(T_SYN, 0.1)                       # the claim matches the model it describes
    laws = {row["name"]: row["law"] for row in asm.constants}
    assert [n for n, law in laws.items() if "PB82" not in law] == ["K water formation"]
    vi = _fake_value(T_SYN, 0.0, max(P_GRID))                               # the informational point
    info = r["informational"]["HCO3_plus_CO3_vs_measured_C_tot"]
    assert info["model_HCO3_plus_CO3_M"] == 2 * vi and info["model_DIC_M_not_comparable"] == 3 * vi
    env = r["execution"]["environment"]
    assert {"python", "numpy", "scipy", "git_head", "git_tree_clean"} <= set(env)
    assert r["execution"]["pinned_run"] is False


# --------------------------------------------------------------------------------------------- end to end, real model
def test_real_model_pass_fail_high_and_fail_low_with_all_controls(tmp_path, ident, ca_pred):
    path, sha = _prereg(tmp_path, ident, ca_pred, 0.02 * ca_pred)
    r = HR.run_holdout(path, sha, tmp_path / "receipt.json")
    assert r["verdict"] == HR.PASS and r["controls_all_as_expected"] is True, r.get("invalid_reasons")
    by = {c["name"]: c for c in r["controls"]}
    assert by["C1"]["outcome"] == HR.FAIL_HIGH and by["C2"]["outcome"] == HR.FAIL_LOW
    assert by["C2"]["rescue"]["status"] == "NEEDED_EXCEEDS_CEILING"
    assert by["C3"]["outcome"] == HR.REFUSED and by["C4"]["outcome"] == HR.REFUSED
    assert r["monotonicity"]["holds"] is True
    on_disk = _strict_load(tmp_path / "receipt.json")
    assert on_disk["model_identity_digest"] == OC.model_identity_digest() == ident["model_identity_digest"]
    assert on_disk["measured_interval"] == [ca_pred - 0.02 * ca_pred, ca_pred + 0.02 * ca_pred]
    pt = on_disk["informational"]["point"]
    assert pt["HCO3_plus_CO3_M"] < pt["DIC_M"]                               # reported separately, not conflated
    path2, sha2 = _prereg(tmp_path, ident, 0.80 * ca_pred, 0.05 * ca_pred)
    assert HR.run_holdout(path2, sha2, tmp_path / "r2.json")["verdict"] == HR.FAIL_HIGH
    path3, sha3 = _prereg(tmp_path, ident, 1.15 * ca_pred, 0.05 * ca_pred, ceiling=0.12)
    r3 = HR.run_holdout(path3, sha3, tmp_path / "r3.json")
    assert r3["verdict"] == HR.FAIL_LOW and r3["rescue"]["status"] == "NEEDED_EXCEEDS_CEILING"
    assert _strict_load(tmp_path / "r3.json")["rescue"]["needed_pco2_atm"] == "EXCEEDS_CEILING"


# --------------------------------------------------------------------------------------------- D6: fresh interpreter
def _child_env():
    env = {k: v for k, v in os.environ.items() if k not in (HR.FRESH_ENV, "PYTHONDONTWRITEBYTECODE",
                                                            "PYTHONPYCACHEPREFIX")}
    env["PYTHONPATH"] = str(REPO)
    return env


def test_D6_main_refuses_outside_a_fresh_isolated_interpreter(tmp_path):
    marker = tmp_path / "cache"
    marker.mkdir()
    code = (f"import sys; from experiments.sandbox_foundation import holdout_guidone_xxv as HR; "
            f"sys.exit(HR.main(['x.json', '{'0' * 64}', {str(tmp_path / 'r.json')!r}]))")
    p = subprocess.run([PY, "-c", code], env={**_child_env(), HR.FRESH_ENV: str(marker)}, cwd=tmp_path,
                       capture_output=True, text=True, timeout=300)
    assert p.returncode == 3, p.stderr
    assert "isolated" in p.stderr and "pycache_prefix" in p.stderr
    assert not (tmp_path / "r.json").exists()


def test_D6_running_code_is_bound_to_the_digested_bytes(tmp_path):
    # a throwaway package stands in for a model module: modified, imported, then restored on disk (p6b); or run with
    # no fresh cache at all (p10's stale-bytecode route).  The in-tree modules imported alongside are the control.
    pkg = tmp_path / "fakepkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    pinned = "def ca(x):\n    return x + 1\n"
    (pkg / "mod.py").write_text(pinned)
    script = textwrap.dedent(f"""
        import json, sys
        sys.path.insert(0, {str(REPO)!r}); sys.path.insert(0, {str(tmp_path)!r})
        from pathlib import Path
        from experiments.sandbox_foundation import holdout_guidone_xxv as HR
        f = Path({str(pkg / 'mod.py')!r})
        mode = sys.argv[1]
        if mode == "toctou":
            f.write_text("def ca(x):\\n    return x + 2\\n")
        import fakepkg.mod
        if mode == "toctou":
            f.write_text({pinned!r})
        print(json.dumps(HR.running_code_problems({{"fakepkg.mod": f.read_bytes()}})))
    """)
    (tmp_path / "probe.py").write_text(script)
    out = {}
    for mode, flags in (("clean", ["-X", f"pycache_prefix={tmp_path / 'c1'}"]),
                        ("toctou", ["-X", f"pycache_prefix={tmp_path / 'c2'}"]),
                        ("no_prefix", [])):
        p = subprocess.run([PY, "-I", *flags, str(tmp_path / "probe.py"), mode], capture_output=True, text=True,
                           timeout=300, cwd=tmp_path)
        assert p.returncode == 0, p.stderr
        out[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    assert out["clean"] == []                                                # in-tree modules + clean fake: bound
    assert out["toctou"] == ["fakepkg.mod: the code that ran is not the code its source bytes compile to"]
    assert out["no_prefix"] == ["no pycache prefix: the bytecode that ran cannot be located"]


def test_D6_end_to_end_main_in_a_fresh_interpreter(tmp_path, ident, ca_pred):
    path, sha = _prereg(tmp_path, ident, ca_pred, 0.02 * ca_pred)
    p = subprocess.run([PY, "-m", HR.RUNNER_MODULE, str(path), sha, str(tmp_path / "receipt.json")],
                       env=_child_env(), cwd=REPO, capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, p.stderr[-3000:]
    r = _strict_load(tmp_path / "receipt.json")
    assert r["verdict"] == HR.PASS and r["controls_all_as_expected"] is True
    assert r["execution"]["pinned_run"] is True and "RUNNING_CODE_BOUND" in r["execution"]["mode"]
    assert json.loads(p.stdout)["verdict"] == HR.PASS
    assert not os.path.exists(r["execution"]["pycache_prefix"])              # the parent removed its temp cache


# --------------------------------------------------------------------------------------------- the schema example
def test_the_documented_example_encodes_prereg_sections_4_to_6_and_is_not_executable(tmp_path):
    raw = EXAMPLE.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    pr, _, m = HR.load_preregistration(EXAMPLE, sha)                         # structurally valid under the loader
    _assert_out_of_box(pr)
    g, rule = pr["state_grid"], pr["verdict_rule"]
    assert len(g["T_K"]) == 3 and len(g["pCO2_atm"]) == 2 and g["logKc_shift"] == [-0.020, 0.0, 0.020]
    assert max(g["T_K"]) - min(g["T_K"]) == pytest.approx(4.0)              # +/- 2 K around a nominal T
    assert rule["fail_low_pco2_ceiling_atm"] == 2.0e-3
    assert {k: rule[k] for k in HR.RULE_TOKENS} == HR.RULE_TOKENS
    assert rule["rescue_corner"] == {"T_K": min(g["T_K"]), "logKc_shift": 0.020}
    by = {c["name"]: c for c in pr["controls"]}
    assert (by["C1"]["kind"], by["C1"]["logKc_shift"], by["C1"]["expected"]) == (HR.LOGKC_SHIFT, 0.60, "FAIL_HIGH")
    assert (by["C2"]["kind"], by["C2"]["logKc_shift"], by["C2"]["expected"]) == (HR.LOGKC_SHIFT, -1.50, "FAIL_LOW")
    assert by["C3"]["kind"] == HR.OFF_TEMPERATURE_CONSTANT and by["C3"]["T_K"] == sorted(g["T_K"])[1]
    assert (by["C4"]["kind"], by["C4"]["T_K"], by["C4"]["expected"]) == (HR.OUT_OF_DOMAIN_TEMPERATURE, 370.0, "REFUSED")
    assert sorted(pr["mandatory_control_kinds"]) == sorted(HR.CONTROL_KINDS)
    tr = json.loads(HR.resolve_repo_path(pr["measured"]["transcription_path"]).read_text())
    assert "SYNTHETIC" in pr["note"] and "SYNTHETIC" in tr["note"] and m["interval"][0] > 0
    with pytest.raises(HR.PreregistrationError, match="runner_sha256"):      # placeholder pins: never executable
        HR.run_holdout(EXAMPLE, sha, tmp_path / "r.json")
    assert not (tmp_path / "r.json").exists()
