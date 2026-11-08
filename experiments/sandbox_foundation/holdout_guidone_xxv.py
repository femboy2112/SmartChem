"""OPERATION XXV Phase III-B -- holdout RUNNER for the open calcite world (research code only).

    PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.holdout_guidone_xxv PREREG.json SHA256 RECEIPT.json

It applies a FROZEN preregistration (docs/research/OPERATION_XXV_PREREGISTRATION.md sections 4-6, encoded as JSON) to
``open_calcite_xxv.build_open_calcite_world`` and writes a receipt.  Order of operations, each step fail-closed:

  1. LOAD.  The preregistration's sha256 must equal the one supplied.  JSON is parsed strictly: a duplicate key at any
     depth, an unknown key, NaN/Infinity, or a missing mandatory control kind is refused.  The measured interval is
     NOT taken from the preregistration: it names a transcription file and its sha256, and the runner computes
     M = [value - u_2sigma, value + u_2sigma] from that file itself.
  2. IDENTITY.  The runner's own source sha256 and the model's ``model_identity_digest`` must equal the pinned
     ``runner_sha256`` / ``model_identity_digest``.  Both are computed from ONE read of the code closure's bytes.
     Under ``__main__`` the run happens in a FRESH ISOLATED interpreter with an EMPTY bytecode cache
     (``-I -X pycache_prefix=<new temp dir>``; the parent re-executes itself), and every in-tree module loaded in
     that interpreter is checked to have executed exactly the code its digested bytes compile to.
  3. CONTROLS FIRST (section 6).  Every control runs before the main grid:
       LOGKC_SHIFT                the shift is ADDED to every grid shift value (every grid point); the full rule is
                                  applied; the verdict must equal ``expected``.
       OFF_TEMPERATURE_CONSTANT   each 25 C constant the existing 25 C calcite / carbonate worlds use (Kc, K1, K2,
                                  K_H, Kw) and a 298.15 K-tagged Davies A and rho_w is injected, one at a time, into a
                                  run at the grid's nominal (middle) T; each must be REFUSED with OffTemperatureConstantError, and
                                  the same slot must ACCEPT the constant produced at T (so the refusal is caused by
                                  the temperature, not by the injection seam).
       OUT_OF_DOMAIN_TEMPERATURE  a run at T outside the calcite law's domain must be REFUSED with
                                  TemperatureLawDomainError.
     Refusals are caught and recorded per control.  If ANY control misbehaves, the verdict is INVALID and the main
     grid is NOT evaluated: no main-grid number appears in the receipt or on stdout.
  4. PREMISE (section 4).  dObs/dpCO2 > 0 STRICTLY for every (T, shift) pair over the grid's pCO2 values (and, when the
     rescue runs, from the grid top to the ceiling at the rescue corner).  A violation makes the run INVALID; for a
     control it makes the control misbehave.
  5. VERDICT (section 5), closed intervals, P = [min, max] over the whole grid, M from the transcription:
       PASS       iff P and M intersect (inclusive);
       FAIL_HIGH  iff min(P) > max(M)  (strict);
       FAIL_LOW   iff max(P) < min(M)  (strict) AND the pCO2 the model needs to reach min(M) at the FIXED rescue corner
                  (the preregistration's (T, shift); section 5: 293.15 K, +0.020, i.e. min T and max shift) exceeds the
                  declared ceiling (strict);
       AMBIGUOUS  otherwise (including: the model refuses at the ceiling).
     A main-grid evaluation that raises makes the run INVALID (the instrument could not complete).

PREREGISTRATION JSON (schema ``smartchem.xxv.holdout_prereg/2``; every key below is required unless marked optional,
and no other key is accepted).  A documented example with SYNTHETIC out-of-box values:
``holdouts/EXAMPLE_PREREG_SCHEMA_xxv.json``.
    schema, holdout_id, note (optional str), runner_sha256, model_identity_digest, model_config ({} or a subset of
    MODEL_CONFIG_KEYS), observable ("Ca_total_M"),
    measured {transcription_path, transcription_sha256, quantity ("Ca_tot_M")},
    state_grid {T_K, logKc_shift, pCO2_atm}  (distinct finite values; >= 2 pCO2 values),
    verdict_rule {kind, pass, fail_high, fail_low (the exact rule tokens below), fail_low_pco2_ceiling_atm (> grid top),
                  rescue_corner {T_K, logKc_shift} (must be (min T, max shift) of the grid), bisection_log10_tol},
    mandatory_control_kinds (must name all three kinds), controls [...], informational_point {T_K, pCO2_atm,
    logKc_shift} (a grid point; section 7, reported only).

IN-PROCESS BOUNDARY (residual, documented).  The checks bind the digests to the bytes on disk AND to the code the fresh
interpreter executed.  They cannot see what code running inside that interpreter does afterwards: a site-packages .pth
hook, a monkeypatch, or a constant re-stamped with the right T_K but a wrong value is out of reach.  A library call to
``run_holdout`` (as the tests make) performs every check except the running-code binding and records
``execution.pinned_run = false``; only ``__main__`` produces a pinned run.

This runner was exercised ONLY with synthetic preregistrations whose states lie outside the reserved holdout region.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import marshal
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from experiments.sandbox_foundation import open_calcite_xxv as OC
from experiments.sandbox_foundation import temperature_law_xxv as TL
from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, KW_25C, SourcedConstant
from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as XXIII
from experiments.sandbox_foundation.carbonate_equilibrium import K1_CARBONIC_25C, K2_CARBONIC_25C, KH_CO2_25C

PREREG_SCHEMA = "smartchem.xxv.holdout_prereg/2"
RECEIPT_SCHEMA = "smartchem.xxv.holdout_receipt/2"
TRANSCRIPTION_SCHEMA = "smartchem.research.measurement_transcription/xxv-1"
RULE_KIND = "interval_overlap_with_pco2_rescue"
RULE_TOKENS = {
    "pass": "closed_interval_intersection_inclusive",
    "fail_high": "min_P_strictly_above_max_M",
    "fail_low": "max_P_strictly_below_min_M_and_needed_pCO2_strictly_above_ceiling",
}
PASS, FAIL_HIGH, FAIL_LOW, AMBIGUOUS = "PASS", "FAIL_HIGH", "FAIL_LOW", "AMBIGUOUS"
INVALID, REFUSED = "INVALID", "REFUSED"
VERDICTS = (PASS, FAIL_HIGH, FAIL_LOW, AMBIGUOUS)

LOGKC_SHIFT = "LOGKC_SHIFT"
OFF_TEMPERATURE_CONSTANT = "OFF_TEMPERATURE_CONSTANT"
OUT_OF_DOMAIN_TEMPERATURE = "OUT_OF_DOMAIN_TEMPERATURE"
CONTROL_KINDS = (LOGKC_SHIFT, OFF_TEMPERATURE_CONSTANT, OUT_OF_DOMAIN_TEMPERATURE)
#: the slots the off-temperature control must inject, one at a time (prereg C3 + the bare-float pair of finding 3)
OFF_T_SLOTS = (OC.KC_SLOT, "K HCO3- formation", "K CO2(aq) formation", "K water formation", OC.KH_SLOT,
               OC.DAVIES_A_SLOT, OC.RHO_W_SLOT)

#: observable -> the transcription quantity it is compared with (same units: mol/L)
OBSERVABLE_FOR_QUANTITY = {"Ca_tot_M": "Ca_total_M"}
MODEL_CONFIG_KEYS = ("include_ion_pairs", "spectator_nacl_M", "kLa_per_s", "k_diss", "kf")

RUNNER_MODULE = "experiments.sandbox_foundation.holdout_guidone_xxv"
REPO = Path(__file__).resolve().parents[2]
FRESH_ENV = "SMARTCHEM_HOLDOUT_FRESH_PYCACHE"
_IN_TREE = "experiments"

UNCERTAINTY_STATEMENT = ("P is a lower bound on the model's own uncertainty (K_H, K1, K2 uncertainties unstated, not "
                         "propagated)")
TIER_STATEMENT = "W (weak, nuisance-limited): cannot by itself satisfy the 2.0-alpha gate"
POWER_STATEMENT = ("prereg section 8 (registered for the Guidone 2025 Table 1 holdout; a synthetic preregistration does "
                   "not inherit it): roughly, only a model biased high by about 15% or low by about 40% could fail "
                   "this rule")
CONSTANTS_CLAIM = ("log Kc (calcite), K_H (CO2), K1, K2, CaHCO3+ and CaCO3(aq): Plummer & Busenberg (1982) analytic "
                   "temperature laws, evaluated at the world T; Kw: the phreeqc.dat 'H2O = OH- + H+' -analytic fit "
                   "(NOT Plummer & Busenberg; the file names no primary source); Davies A: anchored at 0.509 (25 C) "
                   "and scaled by a Malmberg & Maryott (1956) dielectric-constant / Kell density ratio; rho_w: Kell "
                   "(1975).  Every log K is transported molal -> molar at the world T.")
OUTCOME_MEANING = {
    PASS: "CORROBORATED (weak): not falsified at this state; does not validate Kc, a temperature slope or the "
          "activity model separately",
    FAIL_HIGH: "REFUTED at this state; kept and published, no re-tuning under this registration",
    FAIL_LOW: "REFUTED at this state; kept and published, no re-tuning under this registration",
    AMBIGUOUS: "recorded as such; nothing is upgraded",
    INVALID: "the instrument is broken: fix it, re-register and disclose; no verdict is reported",
}


class PreregistrationError(ValueError):
    """The preregistration was refused (hash, schema, transcription, identity, or execution environment)."""


# --------------------------------------------------------------------------------------------- strict JSON
def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise PreregistrationError(f"duplicate JSON key {k!r}; refusing (a reader and the runner could disagree)")
        out[k] = v
    return out


def _no_constant(tok):
    raise PreregistrationError(f"non-finite JSON token {tok}; refusing")


def strict_json(data: bytes, what: str):
    """Parse UTF-8 JSON, refusing duplicate keys at any depth and NaN/Infinity."""
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreregistrationError(f"{what} is not UTF-8 JSON: {exc}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_HEX64 = re.compile(r"[0-9a-f]{64}")


def _keys(obj, what, required, optional=()) -> dict:
    if not isinstance(obj, dict):
        raise PreregistrationError(f"{what} must be an object")
    missing = set(required) - set(obj)
    unknown = set(obj) - set(required) - set(optional)
    if missing or unknown:
        raise PreregistrationError(f"{what}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}")
    return obj


def _num(x, what, *, positive=False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or (positive and x <= 0):
        raise PreregistrationError(f"{what} must be a finite number{' > 0' if positive else ''}")
    return float(x)


def _num_list(v, what, *, positive=False, min_len=1) -> list:
    if not isinstance(v, list) or len(v) < min_len:
        raise PreregistrationError(f"{what} must be a list of >= {min_len} numbers")
    out = [_num(x, what, positive=positive) for x in v]
    if len(set(out)) != len(out):
        raise PreregistrationError(f"{what} has duplicate values")
    return out


def _hex64(v, what) -> str:
    if not (isinstance(v, str) and _HEX64.fullmatch(v)):
        raise PreregistrationError(f"{what} must be a 64-hex lowercase sha256")
    return v


def _str(v, what) -> str:
    if not (isinstance(v, str) and v.strip()):
        raise PreregistrationError(f"{what} must be a non-empty string")
    return v


# --------------------------------------------------------------------------------------------- transcription
def resolve_repo_path(p: str) -> Path:
    """An absolute path as given; a relative one must be a clean repo-relative POSIX path."""
    if os.path.isabs(p):
        return Path(p)
    if "\\" in p or any(part in ("", ".", "..") for part in PurePosixPath(p).parts) or p.endswith("/"):
        raise PreregistrationError(f"transcription_path {p!r} is not a clean repo-relative path")
    return REPO / p


def measured_from_transcription(path, expected_sha256: str, quantity: str) -> dict:
    """{value, u_2sigma, interval: [value - u, value + u], ...} computed from the sha-verified transcription."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise PreregistrationError(f"transcription unreadable: {exc}") from exc
    got = _sha256(data)
    if got != expected_sha256:
        raise PreregistrationError(f"transcription sha256 {got} != pinned {expected_sha256}; refusing")
    tr = strict_json(data, "transcription")
    if not isinstance(tr, dict) or tr.get("schema") != TRANSCRIPTION_SCHEMA:
        raise PreregistrationError(f"transcription schema must be {TRANSCRIPTION_SCHEMA!r}")
    meas = tr.get("measured")
    row = meas.get(quantity) if isinstance(meas, dict) else None
    if not isinstance(row, dict):
        raise PreregistrationError(f"transcription has no measured.{quantity}")
    v = _num(row.get("value"), f"measured.{quantity}.value", positive=True)
    u = _num(row.get("u_2sigma"), f"measured.{quantity}.u_2sigma", positive=True)
    if v - u <= 0:
        raise PreregistrationError(f"measured.{quantity}: value - u_2sigma must be > 0")
    extra = {}
    for k in ("C_tot_M", "pH"):                                  # section 7, informational only
        r = meas.get(k)
        if isinstance(r, dict):
            extra[k] = {"value": _num(r.get("value"), f"measured.{k}.value"),
                        "u_2sigma": _num(r.get("u_2sigma"), f"measured.{k}.u_2sigma", positive=True)}
    return {"transcription_sha256": got, "quantity": quantity, "value": v, "u_2sigma": u,
            "interval": [v - u, v + u], "interval_rule": "value +/- u_2sigma, computed by the runner",
            "informational_quantities": extra}


# --------------------------------------------------------------------------------------------- loading
def _grid_point(obj, what, grid, keys) -> dict:
    _keys(obj, what, keys)
    out = {}
    for k in keys:
        out[k] = _num(obj[k], f"{what}.{k}", positive=k != "logKc_shift")
        if out[k] not in grid[k]:
            raise PreregistrationError(f"{what}.{k} = {out[k]} is not a value of state_grid.{k}")
    return out


def _load_control(c, i, grid) -> dict:
    if not isinstance(c, dict):
        raise PreregistrationError(f"controls[{i}] must be an object")
    kind = c.get("kind")
    what = f"controls[{i}] ({c.get('name')!r})"
    if kind == LOGKC_SHIFT:
        _keys(c, what, ("name", "kind", "logKc_shift", "expected"))
        if c["expected"] not in VERDICTS:
            raise PreregistrationError(f"{what}: expected must be one of {VERDICTS}")
        if _num(c["logKc_shift"], f"{what}.logKc_shift") == 0.0:
            raise PreregistrationError(f"{what}: a zero shift mutates nothing")
    elif kind == OFF_TEMPERATURE_CONSTANT:
        _keys(c, what, ("name", "kind", "T_K", "pCO2_atm", "slots", "expected"))
        _grid_point({"T_K": c["T_K"], "pCO2_atm": c["pCO2_atm"]}, what, grid, ("T_K", "pCO2_atm"))
        Ts = sorted(grid["T_K"])
        if len(Ts) % 2 and float(c["T_K"]) != Ts[len(Ts) // 2]:
            raise PreregistrationError(f"{what}: T_K must be the grid's nominal (middle) temperature {Ts[len(Ts) // 2]}")
        sl = c["slots"]
        if not isinstance(sl, list) or len(sl) != len(set(map(str, sl))) or set(sl) != set(OFF_T_SLOTS):
            raise PreregistrationError(f"{what}: slots must list each of {list(OFF_T_SLOTS)} exactly once")
        if c["expected"] != REFUSED:
            raise PreregistrationError(f"{what}: expected must be {REFUSED!r}")
    elif kind == OUT_OF_DOMAIN_TEMPERATURE:
        _keys(c, what, ("name", "kind", "T_K", "pCO2_atm", "expected"))
        T = _num(c["T_K"], f"{what}.T_K", positive=True)
        if TL.PB82_LOG_KC.T_min_K <= T <= TL.PB82_LOG_KC.T_max_K:
            raise PreregistrationError(f"{what}: T_K {T} lies INSIDE the calcite law's domain; it tests nothing")
        if _num(c["pCO2_atm"], f"{what}.pCO2_atm", positive=True) not in grid["pCO2_atm"]:
            raise PreregistrationError(f"{what}.pCO2_atm is not a grid value")
        if c["expected"] != REFUSED:
            raise PreregistrationError(f"{what}: expected must be {REFUSED!r}")
    else:
        raise PreregistrationError(f"{what}: kind must be one of {CONTROL_KINDS}")
    _str(c["name"], f"{what}.name")
    return c


def load_preregistration(path, expected_sha256: str) -> tuple:
    """(prereg dict, sha256, measured dict).  Refuses on any defect; never evaluates the model."""
    data = Path(path).read_bytes()
    got = _sha256(data)
    if not isinstance(expected_sha256, str) or got != expected_sha256.strip().lower():
        raise PreregistrationError(f"preregistration sha256 {got} != expected {expected_sha256!r}; refusing")
    pr = strict_json(data, "preregistration")
    _keys(pr, "preregistration", ("schema", "holdout_id", "runner_sha256", "model_identity_digest", "model_config",
                                  "observable", "measured", "state_grid", "verdict_rule", "mandatory_control_kinds",
                                  "controls", "informational_point"), optional=("note",))
    if pr["schema"] != PREREG_SCHEMA:
        raise PreregistrationError(f"schema must be {PREREG_SCHEMA!r}")
    _str(pr["holdout_id"], "holdout_id")
    if "note" in pr and not isinstance(pr["note"], str):
        raise PreregistrationError("note must be a string")
    _hex64(pr["runner_sha256"], "runner_sha256")
    _hex64(pr["model_identity_digest"], "model_identity_digest")
    cfg = pr["model_config"]
    if not isinstance(cfg, dict) or set(cfg) - set(MODEL_CONFIG_KEYS):
        raise PreregistrationError(f"model_config keys must be a subset of {MODEL_CONFIG_KEYS}")
    m = _keys(pr["measured"], "measured", ("transcription_path", "transcription_sha256", "quantity"))
    if m["quantity"] not in OBSERVABLE_FOR_QUANTITY or OBSERVABLE_FOR_QUANTITY[m["quantity"]] != pr["observable"]:
        raise PreregistrationError(f"observable/quantity must be one of {OBSERVABLE_FOR_QUANTITY} (quantity -> "
                                   f"observable)")
    _hex64(m["transcription_sha256"], "measured.transcription_sha256")
    measured = measured_from_transcription(resolve_repo_path(_str(m["transcription_path"], "transcription_path")),
                                           m["transcription_sha256"], m["quantity"])
    g = _keys(pr["state_grid"], "state_grid", ("T_K", "logKc_shift", "pCO2_atm"))
    grid = {"T_K": _num_list(g["T_K"], "T_K", positive=True),
            "logKc_shift": _num_list(g["logKc_shift"], "logKc_shift"),
            "pCO2_atm": _num_list(g["pCO2_atm"], "pCO2_atm", positive=True, min_len=2)}
    rule = _keys(pr["verdict_rule"], "verdict_rule", ("kind", "pass", "fail_high", "fail_low",
                                                      "fail_low_pco2_ceiling_atm", "rescue_corner",
                                                      "bisection_log10_tol"))
    if rule["kind"] != RULE_KIND or any(rule[k] != v for k, v in RULE_TOKENS.items()):
        raise PreregistrationError(f"verdict_rule must be kind {RULE_KIND!r} with tokens {RULE_TOKENS}")
    if _num(rule["fail_low_pco2_ceiling_atm"], "ceiling", positive=True) <= max(grid["pCO2_atm"]):
        raise PreregistrationError("fail_low_pco2_ceiling_atm must exceed the grid's largest pCO2")
    tol = _num(rule["bisection_log10_tol"], "bisection_log10_tol", positive=True)
    if tol > 0.1:
        raise PreregistrationError("bisection_log10_tol must be <= 0.1")
    corner = _grid_point(rule["rescue_corner"], "rescue_corner", grid, ("T_K", "logKc_shift"))
    if (corner["T_K"], corner["logKc_shift"]) != (min(grid["T_K"]), max(grid["logKc_shift"])):
        raise PreregistrationError("rescue_corner must be (min T_K, max logKc_shift) of the grid -- the most soluble "
                                   "corner under the declared premise (prereg section 5)")
    _grid_point(pr["informational_point"], "informational_point", grid, ("T_K", "pCO2_atm", "logKc_shift"))
    mand = pr["mandatory_control_kinds"]
    if not isinstance(mand, list) or len(mand) != len(set(map(str, mand))) or set(mand) != set(CONTROL_KINDS):
        raise PreregistrationError(f"mandatory_control_kinds must name each of {list(CONTROL_KINDS)} exactly once")
    ctr = pr["controls"]
    if not isinstance(ctr, list) or not ctr:
        raise PreregistrationError("controls must be a non-empty list (an instrument with no control is not "
                                   "fail-capable)")
    ctr = [_load_control(c, i, grid) for i, c in enumerate(ctr)]
    if len({c["name"] for c in ctr}) != len(ctr):
        raise PreregistrationError("control names must be unique")
    missing = set(mand) - {c["kind"] for c in ctr}
    if missing:
        raise PreregistrationError(f"mandatory control kind(s) {sorted(missing)} have no control; refusing")
    expected_shifts = {c["expected"] for c in ctr if c["kind"] == LOGKC_SHIFT}
    if not {FAIL_HIGH, FAIL_LOW} <= expected_shifts:
        raise PreregistrationError("LOGKC_SHIFT controls must include one expected FAIL_HIGH and one expected FAIL_LOW "
                                   "(the instrument must be fail-capable in both directions)")
    return pr, got, measured


# --------------------------------------------------------------------------------------------- identity
def closure_bytes(root: str = RUNNER_MODULE) -> dict:
    """{module: bytes} for ``root``'s in-tree code closure, each file read ONCE; refused if a second read disagrees."""
    names = OC.code_closure(root)
    out = {}
    for name, sha in names.items():
        data = OC._module_path(name).read_bytes()
        if _sha256(data) != sha:
            raise PreregistrationError(f"{name} changed on disk while its closure was being read; refusing")
        out[name] = data
    return out


def identities(code: dict, cfg: dict) -> dict:
    """runner sha256 and model digest from ONE read of the bytes.  The runner's closure must be the model's closure
    plus the runner itself, so the two pins cover every in-tree byte the runner can execute."""
    model_names = set(OC.code_closure())
    if set(code) != model_names | {RUNNER_MODULE}:
        raise PreregistrationError(f"runner closure {sorted(set(code) - model_names)} reaches in-tree code outside "
                                   f"the model's pinned closure; refusing (it would be unpinned)")
    mid = OC.model_identity_digest_for_code({m: _sha256(code[m]) for m in model_names}, **cfg)
    return {"runner_sha256": _sha256(code[RUNNER_MODULE]), "model_identity_digest": mid,
            "code_closure": {m: _sha256(b) for m, b in sorted(code.items())}}


def _loaded_module(name: str):
    mod = sys.modules.get(name)
    if mod is None:
        main = sys.modules.get("__main__")
        spec = getattr(main, "__spec__", None)
        if spec is not None and spec.name == name:
            mod = main
    return mod


def running_code_problems(code: dict, *, prefix=None) -> list:
    """Every reason the in-tree code loaded in THIS interpreter may differ from the bytes in ``code`` ({module:
    bytes}; modules outside it are read from disk once).  Each loaded in-tree module must have been compiled into the
    bytecode cache under ``prefix`` (default: sys.pycache_prefix) and that bytecode must equal ``compile`` of the
    bytes.  An empty list = the running code is the digested code."""
    prefix = sys.pycache_prefix if prefix is None else prefix
    if not prefix:
        return ["no pycache prefix: the bytecode that ran cannot be located"]
    root = os.path.realpath(prefix) + os.sep
    names = {n for n in sys.modules if n == _IN_TREE or n.startswith(_IN_TREE + ".")} | set(code)
    probs = []
    for name in sorted(names):
        mod = _loaded_module(name)
        if mod is None:
            continue                                         # never imported: nothing of it ran
        spec = getattr(mod, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if origin is None or not origin.endswith(".py"):
            if getattr(mod, "__file__", None) is None:
                continue                                     # namespace package: no code
            probs.append(f"{name}: not loaded from a .py source ({origin!r})")
            continue
        cached = getattr(mod, "__cached__", None) or getattr(spec, "cached", None)
        if not cached or not os.path.realpath(cached).startswith(root):
            probs.append(f"{name}: bytecode {cached!r} is not in the fresh cache {prefix!r}")
            continue
        try:
            pyc = Path(cached).read_bytes()
            ran = marshal.loads(pyc[16:])
        except (OSError, ValueError, EOFError, TypeError) as exc:
            probs.append(f"{name}: bytecode unreadable ({exc})")
            continue
        src = code.get(name)
        if src is None:
            src = Path(origin).read_bytes()
        if ran != compile(src, origin, "exec", dont_inherit=True):
            probs.append(f"{name}: the code that ran is not the code its source bytes compile to")
    return probs


def fresh_interpreter_problems(marker) -> list:
    """The __main__ child must be isolated, write bytecode, and use the empty cache its parent created."""
    probs = []
    if not sys.flags.isolated:
        probs.append("interpreter not started with -I (isolated)")
    if sys.flags.dont_write_bytecode:
        probs.append("bytecode writing disabled: the code that runs could not be checked")
    if not marker or not sys.pycache_prefix or os.path.realpath(sys.pycache_prefix) != os.path.realpath(marker):
        probs.append(f"sys.pycache_prefix {sys.pycache_prefix!r} is not the fresh cache {marker!r}")
    return probs


def _git(*args):
    try:
        p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def environment() -> dict:
    vers = {}
    for dist in ("numpy", "scipy"):
        try:
            vers[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            vers[dist] = None
    head = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=all")
    return {"python": sys.version, "executable": sys.executable, "numpy": vers["numpy"], "scipy": vers["scipy"],
            "git_head": head.strip() if head else None,
            "git_tree_clean": None if status is None else status.strip() == "",
            "git_status_porcelain": None if status is None else status.splitlines()[:50]}


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
                       "Ca_total_M": r.Ca_total_M, "DIC_M": r.DIC_M,
                       "HCO3_plus_CO3_M": r.species_M["HCO3-"] + r.species_M["CO3-2"],
                       "pH_activity": r.pH_activity, "run_identity_digest": r.receipt["run_identity_digest"]}
    return _CACHE[key]


def monotonicity(obs, grid_T, shifts, grid_p, cfg, mid) -> dict:
    """dObs/dpCO2 > 0 STRICTLY between consecutive grid pCO2 values, for every (T, shift) pair."""
    ps = sorted(grid_p)
    bad = []
    for T in grid_T:
        for s in shifts:
            series = [_evaluate(T, s, p, cfg, mid)[obs] for p in ps]
            if not all(b > a for a, b in zip(series, series[1:])):
                bad.append({"T_K": T, "logKc_shift": s})
    return {"holds": not bad, "violations": bad, "pCO2_atm": ps, "rule": "strictly increasing in pCO2"}


def _rescue(obs, corner, p_top, target, ceiling, tol, cfg, mid) -> dict:
    """The pCO2 the model needs at the FIXED rescue corner to reach ``target`` (min of the measured interval)."""
    T, s = corner
    out = {"corner": {"T_K": T, "logKc_shift": s}, "target": target, "ceiling_atm": ceiling,
           "bisection_log10_tol": tol}
    at_top = _evaluate(T, s, p_top, cfg, mid)[obs]
    try:
        at_ceiling = _evaluate(T, s, ceiling, cfg, mid)[obs]
    except Exception as exc:                                     # the model refused at the ceiling: undeterminable
        return {**out, "needed_pco2_atm": None, "status": f"MODEL_REFUSED_AT_CEILING: {type(exc).__name__}: {exc}"}
    out["value_at_ceiling"] = at_ceiling
    if not at_ceiling > at_top:
        return {**out, "needed_pco2_atm": None, "status": "NOT_MONOTONE_GRID_TOP_TO_CEILING", "premise_violated": True}
    if at_ceiling < target:
        return {**out, "needed_pco2_atm": math.inf, "status": "NEEDED_EXCEEDS_CEILING"}
    lo, hi = math.log10(p_top), math.log10(ceiling)
    while hi - lo > tol:
        mid_lp = 0.5 * (lo + hi)
        if _evaluate(T, s, 10.0 ** mid_lp, cfg, mid)[obs] < target:
            lo = mid_lp
        else:
            hi = mid_lp
    return {**out, "needed_pco2_atm": 10.0 ** hi, "bracket_atm": [10.0 ** lo, 10.0 ** hi],
            "status": "NEEDED_AT_OR_BELOW_CEILING"}


def _judge(obs, grid_T, shifts, grid_p, meas, rule, cfg, mid, corner) -> dict:
    """Premise first, then the rule.  verdict None = the premise failed (INVALID / control misbehaved)."""
    mono = monotonicity(obs, grid_T, shifts, grid_p, cfg, mid)
    if not mono["holds"]:
        return {"verdict": None, "monotonicity": mono, "reason": "PREMISE_VIOLATED: dObs/dpCO2 not strictly > 0"}
    evals = [_evaluate(T, s, p, cfg, mid) for T in grid_T for s in shifts for p in grid_p]
    vals = [e[obs] for e in evals]
    pred = (min(vals), max(vals))
    rescue, needed = None, None
    ceiling = float(rule["fail_low_pco2_ceiling_atm"])
    if pred[1] < meas[0]:
        rescue = _rescue(obs, corner, max(grid_p), meas[0], ceiling, float(rule["bisection_log10_tol"]), cfg, mid)
        if rescue.get("premise_violated"):
            return {"verdict": None, "monotonicity": mono, "rescue": rescue,
                    "reason": "PREMISE_VIOLATED: not strictly increasing from the grid top to the ceiling"}
        needed = rescue["needed_pco2_atm"]
    verdict = interval_verdict(pred, meas, needed_pco2=needed, ceiling=ceiling)
    return {"verdict": verdict, "prediction_interval": list(pred), "rescue": rescue, "evaluations": evals,
            "monotonicity": mono}


# --------------------------------------------------------------------------------------------- controls
def _inverse(c: SourcedConstant, name: str) -> SourcedConstant:
    """The same 25 C record for the reverse reaction (K -> 1/K), its T_K tag untouched."""
    return SourcedConstant(name, 1.0 / c.value, c.uncertainty / c.value ** 2, c.units, c.T_K,
                           c.source + " [inverted for the reverse reaction]", c.status, c.note)


def off_temperature_constants() -> dict:
    """{slot: the 25 C constant the existing 25 C calcite / carbonate worlds use}, oriented as the slot's reaction."""
    lk = XXIII.load_constants("nominal")["logk"]["calcite_ksp"]
    return {
        OC.KC_SLOT: XXIII._constant("Ksp_calcite (25 C calcite world)", lk, "solid_equilibrium_xxiii calcite world: "
                                    f"minteq.v4 Calcite log_k {lk}"),
        "K HCO3- formation": _inverse(K2_CARBONIC_25C, "1/K2_carbonic (25 C)"),
        "K CO2(aq) formation": _inverse(K1_CARBONIC_25C, "1/K1_carbonic (25 C)"),
        "K water formation": _inverse(KW_25C, "1/Kw (25 C)"),
        OC.KH_SLOT: KH_CO2_25C,
        OC.DAVIES_A_SLOT: DAVIES_A_25C,
        OC.RHO_W_SLOT: TL.water_density(298.15),
    }


def _at_temperature_constants(asm) -> dict:
    out = {OC.KH_SLOT: asm.gas.henry, OC.DAVIES_A_SLOT: asm.davies_A, OC.RHO_W_SLOT: asm.rho_w}
    for r in asm.rxns:
        law = r.rate_law
        if r.name == "calcite dissolution":
            out[OC.KC_SLOT] = law.ksp
        else:
            out["K " + r.name] = law.K
    return out


def _err(exc) -> dict:
    return {"type": type(exc).__name__, "message": str(exc)[:400]}


def _run_off_temperature(c, cfg) -> dict:
    T, p = float(c["T_K"]), float(c["pCO2_atm"])
    injected = off_temperature_constants()
    at_T = _at_temperature_constants(OC.assemble_open_calcite_world(T, p, **cfg))
    rows, ok = [], True
    for slot in c["slots"]:
        inj = injected[slot]
        row = {"slot": slot, "injected": {"name": inj.name, "T_K": inj.T_K, "value": inj.value, "units": inj.units}}
        try:
            OC.build_open_calcite_world(T, p, substitute={slot: inj}, **cfg)
            row.update(outcome="NOT_REFUSED", refused=False)
        except OC.OffTemperatureConstantError as exc:
            row.update(outcome=REFUSED, refused=True, error=_err(exc))
        except Exception as exc:                                 # refused, but not for the temperature: does not count
            row.update(outcome="WRONG_ERROR", refused=False, error=_err(exc))
        try:                                                     # discriminator: the seam accepts the at-T constant
            OC.assemble_open_calcite_world(T, p, substitute={slot: at_T[slot]}, **cfg)
            row["seam_accepts_at_T_constant"] = True
        except Exception as exc:
            row.update(seam_accepts_at_T_constant=False, seam_error=_err(exc))
        row["as_expected"] = row["refused"] and row["seam_accepts_at_T_constant"]
        ok = ok and row["as_expected"]
        rows.append(row)
    return {"T_K": T, "pCO2_atm": p, "per_slot": rows, "outcome": REFUSED if ok else "MISBEHAVED", "as_expected": ok}


def _run_out_of_domain(c, cfg) -> dict:
    T, p = float(c["T_K"]), float(c["pCO2_atm"])
    try:
        OC.build_open_calcite_world(T, p, **cfg)
        return {"T_K": T, "pCO2_atm": p, "outcome": "NOT_REFUSED", "as_expected": False}
    except TL.TemperatureLawDomainError as exc:
        return {"T_K": T, "pCO2_atm": p, "outcome": REFUSED, "error": _err(exc), "as_expected": True}
    except Exception as exc:
        return {"T_K": T, "pCO2_atm": p, "outcome": "WRONG_ERROR", "error": _err(exc), "as_expected": False}


def run_control(c, obs, grid, meas, rule, cfg, mid) -> dict:
    out = {"name": c["name"], "kind": c["kind"], "expected": c["expected"]}
    if c["kind"] == LOGKC_SHIFT:
        d = float(c["logKc_shift"])
        corner = rule["rescue_corner"]
        try:
            j = _judge(obs, grid["T_K"], [s + d for s in grid["logKc_shift"]], grid["pCO2_atm"], meas, rule, cfg, mid,
                       (float(corner["T_K"]), float(corner["logKc_shift"]) + d))
        except Exception as exc:
            return {**out, "logKc_shift_added": d, "outcome": "ERROR", "error": _err(exc), "as_expected": False}
        res = {**out, "logKc_shift_added": d, "outcome": j["verdict"] or "PREMISE_VIOLATED",
               "monotonicity": j["monotonicity"], "prediction_interval": j.get("prediction_interval"),
               "rescue": j.get("rescue")}
        return {**res, "as_expected": j["verdict"] == c["expected"]}
    try:
        body = _run_off_temperature(c, cfg) if c["kind"] == OFF_TEMPERATURE_CONSTANT else _run_out_of_domain(c, cfg)
    except Exception as exc:
        return {**out, "outcome": "ERROR", "error": _err(exc), "as_expected": False}
    return {**out, **body}


# --------------------------------------------------------------------------------------------- informational
def _informational(pr, obs, grid, measured, cfg, mid) -> dict:
    ip = pr["informational_point"]
    T, p, s = float(ip["T_K"]), float(ip["pCO2_atm"]), float(ip["logKc_shift"])
    e = _evaluate(T, s, p, cfg, mid)
    out = {"weight": "NONE (prereg section 7: reported, not verdict-bearing)", "point": dict(e),
           "rel_deviation_from_measured_value": e[obs] / measured["value"] - 1.0}
    iq = measured["informational_quantities"]
    if "C_tot_M" in iq:
        out["HCO3_plus_CO3_vs_measured_C_tot"] = {
            "model_HCO3_plus_CO3_M": e["HCO3_plus_CO3_M"], "model_DIC_M_not_comparable": e["DIC_M"],
            "measured": iq["C_tot_M"], "note": "the caption defines C_tot = [HCO3-] + [CO3 2-], so DIC is NOT the "
                                               "comparable quantity"}
    if "pH" in iq:
        out["pH_vs_measured"] = {"model_pH_activity": e["pH_activity"], "measured": iq["pH"],
                                 "note": "electrode convention unstated"}
    Ts, ps = sorted(grid["T_K"]), sorted(grid["pCO2_atm"])
    if len(Ts) >= 2:
        a, b = _evaluate(Ts[0], s, p, cfg, mid)[obs], _evaluate(Ts[-1], s, p, cfg, mid)[obs]
        out["dlnObs_dT_percent_per_K"] = 100.0 * math.log(b / a) / (Ts[-1] - Ts[0])
    a, b = _evaluate(T, s, ps[0], cfg, mid)[obs], _evaluate(T, s, ps[-1], cfg, mid)[obs]
    out["pCO2_exponent"] = math.log(b / a) / math.log(ps[-1] / ps[0])
    sh = sorted(grid["logKc_shift"])
    if len(sh) >= 2:
        lo, hi = _evaluate(T, sh[0], p, cfg, mid)[obs], _evaluate(T, sh[-1], p, cfg, mid)[obs]
        out["obs_relative_span_over_shift_range"] = {"shifts": [sh[0], sh[-1]], "rel_span": hi / lo - 1.0}
    return out


# --------------------------------------------------------------------------------------------- the run
def _statements() -> dict:
    return {"uncertainty_statement": UNCERTAINTY_STATEMENT, "tier": TIER_STATEMENT, "power_statement": POWER_STATEMENT,
            "constants_claim": CONSTANTS_CLAIM}


def run_holdout(prereg_path, expected_sha256: str, receipt_path, *, _running_code_check: bool = False) -> dict:
    pr, sha, measured = load_preregistration(prereg_path, expected_sha256)
    cfg = dict(pr["model_config"])
    code = closure_bytes()
    ident = identities(code, cfg)
    if ident["runner_sha256"] != pr["runner_sha256"]:
        raise PreregistrationError(f"runner_sha256 drift: this runner hashes to {ident['runner_sha256']}, the "
                                   f"preregistration pinned {pr['runner_sha256']}; refusing")
    mid = ident["model_identity_digest"]
    if mid != pr["model_identity_digest"]:
        raise PreregistrationError(f"model_identity_digest drift: the code now hashes to {mid}, the preregistration "
                                   f"pinned {pr['model_identity_digest']}; refusing to evaluate a different model")
    execution = {"pinned_run": False, "mode": "IN_PROCESS_LIBRARY_CALL (running code NOT bound to the digests)"}
    if _running_code_check:
        for name in code:                                        # load the WHOLE closure now, so no in-tree code
            if name != RUNNER_MODULE:                            # is first compiled after the binding check
                importlib.import_module(name)
        probs = running_code_problems(code)
        if probs:
            raise PreregistrationError(f"the running code is not the digested code: {probs}; refusing")
        execution = {"pinned_run": True, "pycache_prefix": sys.pycache_prefix,
                     "mode": "FRESH_ISOLATED_INTERPRETER, EMPTY_BYTECODE_CACHE, RUNNING_CODE_BOUND_TO_DIGESTS",
                     "residual": "in-process: code executing inside this interpreter after the check is not seen"}
    execution["environment"] = environment()
    obs = pr["observable"]
    meas = tuple(measured["interval"])
    g = pr["state_grid"]
    grid = {k: [float(x) for x in g[k]] for k in ("T_K", "logKc_shift", "pCO2_atm")}
    rule = pr["verdict_rule"]
    receipt = {
        "schema": RECEIPT_SCHEMA, "holdout_id": pr["holdout_id"], "preregistration_path": str(prereg_path),
        "preregistration_sha256": sha, "runner_sha256": ident["runner_sha256"], "model_identity_digest": mid,
        "code_closure": ident["code_closure"], "model_config": cfg, "execution": execution, "observable": obs,
        "measured": {**measured, "transcription_path": pr["measured"]["transcription_path"]},
        "measured_interval": list(meas), "state_grid": grid, "verdict_rule": rule, **_statements(),
    }
    # 1. controls FIRST
    controls = [run_control(c, obs, grid, meas, rule, cfg, mid) for c in pr["controls"]]
    receipt["controls"] = controls
    receipt["controls_all_as_expected"] = bool(controls) and all(c["as_expected"] for c in controls)
    if not receipt["controls_all_as_expected"]:
        bad = [c["name"] for c in controls if not c["as_expected"]]
        return _write(receipt_path, {**receipt, "verdict": INVALID, "outcome_meaning": OUTCOME_MEANING[INVALID],
                                     "invalid_reasons": [f"CONTROL_MISBEHAVED: {bad}"],
                                     "main_grid": "NOT EVALUATED (a control misbehaved)"})
    # 2. the main grid: premise, then the rule
    corner = (float(rule["rescue_corner"]["T_K"]), float(rule["rescue_corner"]["logKc_shift"]))
    try:
        main = _judge(obs, grid["T_K"], grid["logKc_shift"], grid["pCO2_atm"], meas, rule, cfg, mid, corner)
    except Exception as exc:
        return _write(receipt_path, {**receipt, "verdict": INVALID, "outcome_meaning": OUTCOME_MEANING[INVALID],
                                     "invalid_reasons": [f"MAIN_GRID_MODEL_ERROR: {type(exc).__name__}"],
                                     "main_grid": "NOT REPORTED (evaluation raised)"})
    if main["verdict"] is None:
        viol = main["monotonicity"]["violations"]
        return _write(receipt_path, {**receipt, "verdict": INVALID, "outcome_meaning": OUTCOME_MEANING[INVALID],
                                     "invalid_reasons": [main["reason"]],
                                     "premise_violations": viol or "grid top to ceiling at the rescue corner",
                                     "main_grid": "NOT REPORTED (premise violated)"})
    receipt.update(verdict=main["verdict"], outcome_meaning=OUTCOME_MEANING[main["verdict"]],
                   prediction_interval=main["prediction_interval"], rescue=main["rescue"],
                   monotonicity=main["monotonicity"], evaluations=main["evaluations"],
                   informational=_informational(pr, obs, grid, measured, cfg, mid))
    return _write(receipt_path, receipt)


def _write(receipt_path, receipt) -> dict:
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


def stdout_summary(r: dict) -> dict:
    """What __main__ prints.  An INVALID run prints no main-grid number (there is none in its receipt either)."""
    if r["verdict"] == INVALID:
        return {"verdict": INVALID, "invalid_reasons": r["invalid_reasons"],
                "controls": {c["name"]: c["as_expected"] for c in r["controls"]}}
    return {k: r[k] for k in ("verdict", "prediction_interval", "measured_interval", "controls_all_as_expected")}


# --------------------------------------------------------------------------------------------- __main__
def _reexec_fresh(argv) -> int:
    """Re-run this module in a fresh isolated interpreter whose bytecode cache is a new, empty directory."""
    tmp = tempfile.mkdtemp(prefix="smartchem_holdout_pyc_")
    boot = (f"import sys, runpy; sys.path.insert(0, {str(REPO)!r}); "
            f"runpy.run_module({RUNNER_MODULE!r}, run_name='__main__', alter_sys=True)")
    try:
        return subprocess.run([sys.executable, "-I", "-X", f"pycache_prefix={tmp}", "-c", boot, *argv],
                              env={**os.environ, FRESH_ENV: tmp}).returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)               # our own mkdtemp, nothing else


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print("usage: holdout_guidone_xxv PREREG.json EXPECTED_SHA256 RECEIPT.json", file=sys.stderr)
        return 2
    marker = os.environ.get(FRESH_ENV)
    if marker is None:
        return _reexec_fresh(argv)
    probs = fresh_interpreter_problems(marker)
    if probs:
        print(json.dumps({"refused": probs}), file=sys.stderr)
        return 3
    try:
        r = run_holdout(argv[0], argv[1], argv[2], _running_code_check=True)
    except PreregistrationError as exc:
        print(json.dumps({"refused": str(exc)}), file=sys.stderr)
        return 4
    print(json.dumps(stdout_summary(r), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
