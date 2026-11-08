"""OPERATION XXV Phase III-B -- holdout RUNNER for the open calcite world (research code only).

    PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.holdout_guidone_xxv PREREG.json SHA256 RECEIPT.json

It evaluates ``open_calcite_xxv.build_open_calcite_world`` on the state grid a FROZEN preregistration declares, applies
the preregistration's verdict rule, runs its mutated-source controls, and writes a receipt.  It refuses (before any
model evaluation) when the preregistration's sha256 differs from the one supplied, when its schema is malformed, or when
its pinned ``model_identity_digest`` differs from the code that would run.

VERDICT RULE ("interval_overlap_with_pco2_rescue"), on closed intervals:
    pred = [min, max] of the observable over the whole grid (T x logKc_shift x pCO2); meas = the measured interval.
    PASS       iff pred and meas intersect;
    FAIL_HIGH  iff min(pred) > max(meas);
    FAIL_LOW   iff max(pred) < min(meas) AND the pCO2 the model needs to reach min(meas) at the MOST-SOLUBLE grid
               corner (the (T, shift) with the largest observable at the largest grid pCO2) exceeds the declared ceiling;
    AMBIGUOUS  otherwise (including: the model refuses at the ceiling, or the observable is not monotone in pCO2 there).
The rescue search assumes the observable increases with pCO2, so only such observables are accepted.  The needed pCO2
is located by bisection in log10(pCO2) when it lies at or below the ceiling (reported, verdict AMBIGUOUS).

This runner was exercised ONLY with synthetic preregistrations whose states lie outside the reserved holdout region.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from experiments.sandbox_foundation import open_calcite_xxv as OC

PREREG_SCHEMA = "smartchem.xxv.holdout_prereg/1"
RECEIPT_SCHEMA = "smartchem.xxv.holdout_receipt/1"
RULE_KIND = "interval_overlap_with_pco2_rescue"
PASS, FAIL_HIGH, FAIL_LOW, AMBIGUOUS = "PASS", "FAIL_HIGH", "FAIL_LOW", "AMBIGUOUS"
VERDICTS = (PASS, FAIL_HIGH, FAIL_LOW, AMBIGUOUS)

#: observables accepted (all increase with pCO2 in this model, which the rescue search requires)
OBSERVABLES = ("Ca_total_M", "DIC_M", "Ca_total_molal_equiv", "DIC_molal_equiv")
MODEL_CONFIG_KEYS = ("include_ion_pairs", "spectator_nacl_M", "kLa_per_s", "k_diss", "kf")


class PreregistrationError(ValueError):
    """The preregistration was refused (hash, schema, or model-identity mismatch)."""


# --------------------------------------------------------------------------------------------- loading
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finite_list(v, what, *, positive=False) -> list:
    if not isinstance(v, list) or not v:
        raise PreregistrationError(f"{what} must be a non-empty list")
    out = []
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or (positive and x <= 0):
            raise PreregistrationError(f"{what} entries must be finite{' and > 0' if positive else ''}")
        out.append(float(x))
    return out


def load_preregistration(path, expected_sha256: str) -> tuple:
    """(prereg dict, sha256).  Refuses on a hash mismatch or a malformed schema; never evaluates the model."""
    data = Path(path).read_bytes()
    got = _sha256(data)
    if not isinstance(expected_sha256, str) or got != expected_sha256.strip().lower():
        raise PreregistrationError(f"preregistration sha256 {got} != expected {expected_sha256!r}; refusing")
    try:
        pr = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreregistrationError(f"preregistration is not UTF-8 JSON: {exc}") from exc
    if not isinstance(pr, dict) or pr.get("schema") != PREREG_SCHEMA:
        raise PreregistrationError(f"schema must be {PREREG_SCHEMA!r}")
    if pr.get("observable") not in OBSERVABLES:
        raise PreregistrationError(f"observable must be one of {OBSERVABLES}")
    meas = _finite_list(pr.get("measured_interval"), "measured_interval")
    if len(meas) != 2 or meas[0] > meas[1]:
        raise PreregistrationError("measured_interval must be [lo, hi] with lo <= hi")
    grid = pr.get("state_grid")
    if not isinstance(grid, dict) or set(grid) != {"T_K", "logKc_shift", "pCO2_atm"}:
        raise PreregistrationError("state_grid must have exactly T_K, logKc_shift, pCO2_atm")
    _finite_list(grid["T_K"], "T_K", positive=True)
    _finite_list(grid["logKc_shift"], "logKc_shift")
    _finite_list(grid["pCO2_atm"], "pCO2_atm", positive=True)
    cfg = pr.get("model_config", {})
    if not isinstance(cfg, dict) or set(cfg) - set(MODEL_CONFIG_KEYS):
        raise PreregistrationError(f"model_config keys must be a subset of {MODEL_CONFIG_KEYS}")
    rule = pr.get("verdict_rule")
    if not isinstance(rule, dict) or rule.get("kind") != RULE_KIND:
        raise PreregistrationError(f"verdict_rule.kind must be {RULE_KIND!r}")
    _finite_list([rule.get("fail_low_pco2_ceiling_atm")], "fail_low_pco2_ceiling_atm", positive=True)
    _finite_list([rule.get("bisection_log10_tol", 0.01)], "bisection_log10_tol", positive=True)
    ctr = pr.get("mutated_source_controls", [])
    if not isinstance(ctr, list):
        raise PreregistrationError("mutated_source_controls must be a list")
    for c in ctr:
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) or c.get("expected_verdict") not in VERDICTS:
            raise PreregistrationError("each control needs a name and an expected_verdict in " + str(VERDICTS))
        _finite_list([c.get("logKc_shift")], "control logKc_shift")
    if not isinstance(pr.get("model_identity_digest"), str):
        raise PreregistrationError("model_identity_digest (the pinned model) is required")
    return pr, got


# --------------------------------------------------------------------------------------------- the generic rule
def interval_verdict(pred: tuple, meas: tuple, *, needed_pco2=None, ceiling=None) -> str:
    """The interval rule.  ``needed_pco2`` is the rescue result: a float (pCO2 needed, atm), math.inf (needed exceeds the
    ceiling), or None (could not be determined -> AMBIGUOUS when under-predicting)."""
    plo, phi = float(min(pred)), float(max(pred))
    mlo, mhi = float(min(meas)), float(max(meas))
    if plo <= mhi and mlo <= phi:
        return PASS
    if plo > mhi:
        return FAIL_HIGH
    if needed_pco2 is not None and ceiling is not None and needed_pco2 > ceiling:
        return FAIL_LOW
    return AMBIGUOUS


# --------------------------------------------------------------------------------------------- evaluation
_CACHE: dict = {}


def _evaluate(T, shift, p, cfg, mid) -> dict:
    key = (mid, float(T), float(shift), float(p), json.dumps(cfg, sort_keys=True))
    if key not in _CACHE:
        r = OC.build_open_calcite_world(T, p, logKc_shift=shift, **cfg)
        _CACHE[key] = {"T_K": float(T), "logKc_shift": float(shift), "pCO2_atm": float(p),
                       **{o: getattr(r, o) for o in OBSERVABLES}, "pH_activity": r.pH_activity,
                       "run_identity_digest": r.receipt["run_identity_digest"]}
    return _CACHE[key]


def _rescue(obs, grid_T, shifts, grid_p, target, ceiling, tol, cfg, mid) -> dict:
    """The pCO2 the model needs at the most-soluble corner to reach ``target`` (min of the measured interval)."""
    p_top = max(grid_p)
    corner = max(((T, s) for T in grid_T for s in shifts), key=lambda ts: _evaluate(ts[0], ts[1], p_top, cfg, mid)[obs])
    out = {"corner": {"T_K": corner[0], "logKc_shift": corner[1]}, "target": target, "ceiling_atm": ceiling}
    series = [_evaluate(corner[0], corner[1], p, cfg, mid)[obs] for p in sorted(grid_p)]
    if any(b < a for a, b in zip(series, series[1:])):
        return {**out, "needed_pco2_atm": None, "status": "NOT_MONOTONE_IN_PCO2_AT_CORNER"}
    if ceiling <= p_top:
        return {**out, "needed_pco2_atm": math.inf, "status": "CEILING_AT_OR_BELOW_GRID_TOP"}
    try:
        at_ceiling = _evaluate(corner[0], corner[1], ceiling, cfg, mid)[obs]
    except Exception as exc:                                     # the model refused at the ceiling: undeterminable
        return {**out, "needed_pco2_atm": None, "status": f"MODEL_REFUSED_AT_CEILING: {type(exc).__name__}: {exc}"}
    out["value_at_ceiling"] = at_ceiling
    if at_ceiling < target:
        return {**out, "needed_pco2_atm": math.inf, "status": "NEEDED_EXCEEDS_CEILING"}
    lo, hi = math.log10(p_top), math.log10(ceiling)
    while hi - lo > tol:
        mid_lp = 0.5 * (lo + hi)
        if _evaluate(corner[0], corner[1], 10.0 ** mid_lp, cfg, mid)[obs] < target:
            lo = mid_lp
        else:
            hi = mid_lp
    return {**out, "needed_pco2_atm": 10.0 ** hi, "bracket_atm": [10.0 ** lo, 10.0 ** hi],
            "status": "NEEDED_AT_OR_BELOW_CEILING"}


def _judge(obs, grid_T, shifts, grid_p, meas, rule, cfg, mid) -> dict:
    evals = [_evaluate(T, s, p, cfg, mid) for T in grid_T for s in shifts for p in grid_p]
    vals = [e[obs] for e in evals]
    pred = (min(vals), max(vals))
    rescue = None
    needed = None
    ceiling = float(rule["fail_low_pco2_ceiling_atm"])
    if pred[1] < meas[0]:
        rescue = _rescue(obs, grid_T, shifts, grid_p, meas[0], ceiling, float(rule.get("bisection_log10_tol", 0.01)),
                         cfg, mid)
        needed = rescue["needed_pco2_atm"]
    verdict = interval_verdict(pred, meas, needed_pco2=needed, ceiling=ceiling)
    return {"prediction_interval": list(pred), "verdict": verdict, "rescue": rescue, "evaluations": evals}


def run_holdout(prereg_path, expected_sha256: str, receipt_path) -> dict:
    pr, sha = load_preregistration(prereg_path, expected_sha256)
    cfg = dict(pr.get("model_config", {}))
    mid = OC.model_identity_digest(**cfg)
    if mid != pr["model_identity_digest"]:
        raise PreregistrationError(f"model_identity_digest drift: the code now hashes to {mid}, the preregistration "
                                   f"pinned {pr['model_identity_digest']}; refusing to evaluate a different model")
    obs = pr["observable"]
    meas = tuple(float(x) for x in pr["measured_interval"])
    g = pr["state_grid"]
    grid_T, shifts, grid_p = ([float(x) for x in g[k]] for k in ("T_K", "logKc_shift", "pCO2_atm"))
    rule = pr["verdict_rule"]
    main = _judge(obs, grid_T, shifts, grid_p, meas, rule, cfg, mid)
    controls = []
    for c in pr.get("mutated_source_controls", []):
        j = _judge(obs, grid_T, [float(c["logKc_shift"])], grid_p, meas, rule, cfg, mid)
        controls.append({"name": c["name"], "logKc_shift": float(c["logKc_shift"]),
                         "expected_verdict": c["expected_verdict"], "verdict": j["verdict"],
                         "as_expected": j["verdict"] == c["expected_verdict"],
                         "differs_from_main": j["verdict"] != main["verdict"],
                         "prediction_interval": j["prediction_interval"], "rescue": j["rescue"]})
    receipt = {
        "schema": RECEIPT_SCHEMA, "preregistration_path": str(prereg_path), "preregistration_sha256": sha,
        "runner_sha256": _sha256(Path(__file__).read_bytes()), "model_identity_digest": mid, "model_config": cfg,
        "observable": obs, "measured_interval": list(meas), "verdict_rule": rule,
        "verdict": main["verdict"], "prediction_interval": main["prediction_interval"], "rescue": main["rescue"],
        "evaluations": main["evaluations"], "controls": controls,
        "controls_all_as_expected": all(c["as_expected"] for c in controls),
        "claim": "model-vs-measurement verdict under the preregistered rule; the model's constants are P&B (1982)",
    }
    receipt = _strict(receipt)
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return receipt


def _strict(obj):
    """Strict-JSON form: an infinite 'needed pCO2' becomes the token EXCEEDS_CEILING; no NaN/Infinity survives."""
    if isinstance(obj, dict):
        return {k: _strict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strict(v) for v in obj]
    if isinstance(obj, float) and math.isinf(obj) and obj > 0:
        return "EXCEEDS_CEILING"
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("non-finite value in a holdout receipt")
    return obj


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: holdout_guidone_xxv PREREG.json EXPECTED_SHA256 RECEIPT.json")
    r = run_holdout(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps({k: r[k] for k in ("verdict", "prediction_interval", "measured_interval",
                                        "controls_all_as_expected")}, indent=2))
