"""The committed harness itself: validate() must pass, and must be able to FAIL (non-vacuous)."""
from experiments.sandbox_foundation import run_probes


def test_validate_passes_and_reports_every_probe():
    ok, summ = run_probes.validate()
    assert ok, [k for k, v in summ["checks"].items() if not v]
    assert set(summ) >= {"A", "B", "C", "D", "checks", "limits"}
    assert 0.8 <= summ["D"]["observed_convergence_order"] <= 1.3


def test_validate_can_fail_when_a_limit_is_tightened_past_what_is_measured(monkeypatch):
    monkeypatch.setitem(run_probes.LIMITS, "analytic_euler_tracer", 1e-9)   # Euler error is ~1e-3: must now FAIL
    ok, summ = run_probes.validate()
    assert not ok and not summ["checks"]["A.closed_form"]

