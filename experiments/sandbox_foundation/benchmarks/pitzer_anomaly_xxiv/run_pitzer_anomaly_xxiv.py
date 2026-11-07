"""OPERATION XXIV-III-B -- why PHREEQC/pitzer.dat misses NIST SRM 191d by -0.074 in the convention-free comparison.

XXIII (CONVENTION_BRIDGE_VERDICT.md) recorded C2 = -0.0741 for the 191d carbonate buffer with pitzer.dat and left it
DARK.  This harness reproduces that number from a VENDORED, SHA-pinned copy of the exact pitzer.dat bytes
(phreeqpython 1.6.2 package data; byte-identical to upstream phreeqc3 at commit 265f63fa6f per the delegated history
scan), then runs single-factor ABLATIONS on temporary COPIES.  The pinned file is never edited and no constant is
adopted from an ablation: the ablations ATTRIBUTE the residual, they do not tune the reference.

Cells (each one change from P0):
  P0  pinned pitzer.dat                                   -- must reproduce the recorded -0.07406745913108281 exactly
  P1  beta2(Na+, HCO3-) = 8.22 (and its T-term -0.049) -> 0     -- the -B2 line added by the 2015 re-parameterization
  P2  PITZER -MacInnes false                               -- the pH scaling convention (C2 must NOT move: the
                                                              acidity function p(aH gCl) is convention-free)
The compared quantity is identical to XXIII's C2: p(aH gCl) from PHREEQC's la_H+, la_Cl- and m_Cl- (1e-7 mol/kgw NaCl
trace) minus the measured acidity function pH(S)_A1 + A sqrt(I)/(1 + 1.5 sqrt(I)) at PHREEQC's I.

Requires phreeqpython (an OPTIONAL dependency: the dev venv has it, hosted CI does not -- the tests skip the PHREEQC
cells there and still verify the pinned bytes).

    PYTHONPATH=. python -m experiments.sandbox_foundation.benchmarks.pitzer_anomaly_xxiv.run_pitzer_anomaly_xxiv
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from experiments.sandbox_foundation.benchmarks.measured_buffers_xxiii import run_convention_bridge_xxiii as H

HERE = Path(__file__).resolve().parent
DB = HERE / "db" / "pitzer.dat"
DB_SHA256 = "eb5051704fad461c4e5325721afc7b9025fad7c2906f72ed48ae182aa2c1a5c9"
RECORDED_XXIII_C2 = -0.07406745913108281                 # result_convention_bridge_xxiii.json, pitzer.dat cell
B2_LINE = b"  HCO3-     Na+       8.22          0           0        -0.049 "
B2_ZERO = b"  HCO3-     Na+       0             0           0         0     "


def pinned_bytes() -> bytes:
    data = DB.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != DB_SHA256:
        raise ValueError(f"pitzer.dat sha256 {got} != pinned {DB_SHA256}; refusing drifted parameters")
    return data


def cells() -> dict:
    base = pinned_bytes()
    if base.count(B2_LINE) != 1:
        raise ValueError("the beta2(Na+, HCO3-) line is not present exactly once in the pinned file")
    if base.count(b"\nPITZER\n") != 1:
        raise ValueError("the PITZER block header is not present exactly once")
    return {"P0_pinned": base,
            "P1_beta2_NaHCO3_zeroed": base.replace(B2_LINE, B2_ZERO),
            "P2_MacInnes_false": base.replace(b"\nPITZER\n", b"\nPITZER\n-MacInnes false\n")}


def c2(db_path: str) -> dict:
    meas = H.MEASURED["carbonate_191d"]
    ref = H.phreeqc_reference(db_path, H._phreeqc_solution("carbonate_191d"))
    if ref is None:
        raise RuntimeError("phreeqpython is not available")
    meas_acidity = meas["pH_S_A1"] + H.bg_minus_log_gamma_cl(ref["ionic_strength"], H.BG_A)
    return {"C2_residual": ref["p_aH_gCl"] - meas_acidity, "p_aH_gCl": ref["p_aH_gCl"],
            "ionic_strength": ref["ionic_strength"], "pH_phreeqc": ref["pH_phreeqc"],
            "log_gamma_Cl": ref["log_gamma_Cl"], "U_R": meas["k_R"] * meas["u_meas"]}


def run() -> dict:
    out = {"database_sha256": DB_SHA256, "recorded_xxiii_C2": RECORDED_XXIII_C2, "cells": {}}
    with tempfile.TemporaryDirectory(prefix="xxiv_pitzer_") as tmp:
        for name, data in cells().items():
            p = Path(tmp) / f"{name}.dat"
            p.write_bytes(data)
            out["cells"][name] = c2(str(p))
    p0 = out["cells"]["P0_pinned"]["C2_residual"]
    out["P0_reproduces_xxiii_exactly"] = p0 == RECORDED_XXIII_C2
    out["P1_attribution"] = out["cells"]["P1_beta2_NaHCO3_zeroed"]["C2_residual"] - p0
    out["P2_shift"] = out["cells"]["P2_MacInnes_false"]["C2_residual"] - p0
    return out


def main() -> int:
    res = run()
    (HERE / "result_pitzer_anomaly_xxiv.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if res["P0_reproduces_xxiii_exactly"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
