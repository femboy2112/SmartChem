"""OPERATION XXIV-III-B -- the pitzer.dat 191d anomaly: pinned bytes always; PHREEQC cells where phreeqpython exists."""
from __future__ import annotations

import json

import pytest

from experiments.sandbox_foundation.benchmarks.pitzer_anomaly_xxiv import run_pitzer_anomaly_xxiv as P


def test_pinned_bytes_and_the_single_factor_cells_are_well_formed():
    cells = P.cells()
    assert set(cells) == {"P0_pinned", "P1_beta2_NaHCO3_zeroed", "P2_MacInnes_false"}
    assert cells["P1_beta2_NaHCO3_zeroed"].count(P.B2_LINE) == 0 and cells["P0_pinned"].count(P.B2_LINE) == 1
    assert len(cells["P1_beta2_NaHCO3_zeroed"]) == len(cells["P0_pinned"])          # exactly one line rewritten


def test_committed_result_records_the_attribution():
    res = json.loads((P.HERE / "result_pitzer_anomaly_xxiv.json").read_text())
    assert res["P0_reproduces_xxiii_exactly"] is True
    assert res["P1_attribution"] == pytest.approx(0.0792, abs=2e-4)
    assert abs(res["P2_shift"]) < 1e-9                       # the acidity function is MacInnes-convention-free
    assert res["cells"]["P1_beta2_NaHCO3_zeroed"]["C2_residual"] > res["cells"]["P1_beta2_NaHCO3_zeroed"]["U_R"]


def test_live_reproduction_when_phreeqc_is_available():
    pytest.importorskip("phreeqpython")
    res = P.run()
    assert res["P0_reproduces_xxiii_exactly"] is True
    assert res["cells"]["P1_beta2_NaHCO3_zeroed"]["C2_residual"] == pytest.approx(0.0051433, abs=1e-6)
