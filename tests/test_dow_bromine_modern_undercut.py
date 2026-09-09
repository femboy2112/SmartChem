"""Arithmetic and claim-boundary pins for the modern Smackover bromine comparison."""
import json
from pathlib import Path

from experiments import dow_bromine_modern_undercut_probe as probe


def test_disclosed_inputs_and_reconstruction_receipt_agree():
    receipt = json.loads((Path(__file__).parents[1] / "experiments" /
                          "dow_bromine_modern_undercut_recon_2026_09_09.json").read_text())
    inputs = receipt["magnolia_2026_1p_inputs"]
    assert inputs["sales_production_kt"] == 74
    assert inputs["field_and_plant_opex_musd"] == 126.0
    assert receipt["primary_source"]["sha256"] == probe.SOURCE_SHA256


def test_base_case_and_uncertainty_discriminator():
    probe.validate()
    result = probe.metrics()
    assert result["cash_outflow_usd_per_kg"] < probe.MINUS_45_USD_PER_KG
    assert result["minus_45_high_opex_margin_usd_per_kg"] < 0
    assert result["minus_30_high_opex_margin_usd_per_kg"] > 0


def test_report_never_overstates_observed_or_production_admission():
    result = probe.report()
    assert result["status"] == "UNDERCUT_AT_SPOT_AND_MINUS_30"
    assert "forecast" in result["epistemic_status"]
    assert any("not observed" in item for item in result["claim_boundary"])
    assert any("not admitted" in item for item in result["claim_boundary"])
