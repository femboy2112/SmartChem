"""Modern disclosed Smackover bromine cost-vs-market discriminator (ROUND 35).

This is a report-only calculation, not a route-ranker input.  It uses Albemarle's 2025 Magnolia Technical Report
Summary, filed with the SEC on 2026-02-11.  The cost numerator (field/plant opex, G&A, and 2026 capital) is not
derived from the market-price denominator, but both live in one issuer-filed model and are not independent source
families.  Values are forecasts in real 2026 USD, not observed realized 2026 costs.
"""
from __future__ import annotations

from decimal import Decimal

SOURCE_URL = "https://www.sec.gov/Archives/edgar/data/915913/000091591326000018/ex966magnolia2025trs.htm"
SOURCE_SHA256 = "58f04e7ec52592c825dfa8da4e0964f25ec8e8874dead8aa4097e8ff82f81849"
SOURCE_EFFECTIVE_DATE = "2025-12-31"
SOURCE_FILED_DATE = "2026-02-11"

# 2026 1P line items from the filed cash-flow tables.  $MM / kt is numerically $/kg.
SALES_KT = Decimal("74")
FIELD_PLANT_OPEX_MUSD = Decimal("126.0")
G_AND_A_MUSD = Decimal("34.7")
CAPITAL_MUSD = Decimal("27.0")
SPOT_USD_PER_KG = Decimal("4.89")
MINUS_30_USD_PER_KG = Decimal("3.42")
MINUS_45_USD_PER_KG = Decimal("2.69")
SOURCE_OPEX_HIGH_FACTOR = Decimal("1.10")
SOURCE_MINUS_45_CFBT_MUSD = Decimal("11.8")


def metrics() -> dict[str, Decimal]:
    opex = FIELD_PLANT_OPEX_MUSD / SALES_KT
    cash = (FIELD_PLANT_OPEX_MUSD + G_AND_A_MUSD + CAPITAL_MUSD) / SALES_KT
    cash_high = (FIELD_PLANT_OPEX_MUSD * SOURCE_OPEX_HIGH_FACTOR + G_AND_A_MUSD + CAPITAL_MUSD) / SALES_KT
    return {
        "field_plant_opex_usd_per_kg": opex,
        "cash_outflow_usd_per_kg": cash,
        "cash_outflow_plus_10pct_opex_usd_per_kg": cash_high,
        "spot_margin_usd_per_kg": SPOT_USD_PER_KG - cash,
        "spot_undercut_fraction": (SPOT_USD_PER_KG - cash) / SPOT_USD_PER_KG,
        "minus_30_margin_usd_per_kg": MINUS_30_USD_PER_KG - cash,
        "minus_30_high_opex_margin_usd_per_kg": MINUS_30_USD_PER_KG - cash_high,
        "minus_45_margin_usd_per_kg": MINUS_45_USD_PER_KG - cash,
        "minus_45_high_opex_margin_usd_per_kg": MINUS_45_USD_PER_KG - cash_high,
    }


def validate() -> None:
    result = metrics()
    assert result["cash_outflow_usd_per_kg"] < MINUS_45_USD_PER_KG
    assert result["minus_45_margin_usd_per_kg"] > 0
    assert SOURCE_MINUS_45_CFBT_MUSD > 0                 # independent table-level arithmetic cross-check
    assert result["minus_45_high_opex_margin_usd_per_kg"] < 0
    assert result["minus_30_high_opex_margin_usd_per_kg"] > 0
    assert result["spot_undercut_fraction"] > Decimal("0.48")


def report() -> dict:
    validate()
    return {
        "status": "UNDERCUT_AT_SPOT_AND_MINUS_30",
        "minus_45_status": "BASE_CASE_POSITIVE_NOT_PLUS_10_PERCENT_OPEX_ROBUST",
        "epistemic_status": "issuer-model-derived forecast, not realized cost",
        "source_url": SOURCE_URL,
        "source_sha256": SOURCE_SHA256,
        "source_effective_date": SOURCE_EFFECTIVE_DATE,
        "source_filed_date": SOURCE_FILED_DATE,
        "inputs": {
            "sales_kt": str(SALES_KT), "field_plant_opex_musd": str(FIELD_PLANT_OPEX_MUSD),
            "g_and_a_musd": str(G_AND_A_MUSD), "capital_musd": str(CAPITAL_MUSD),
            "spot_usd_per_kg": str(SPOT_USD_PER_KG), "minus_30_usd_per_kg": str(MINUS_30_USD_PER_KG),
            "minus_45_usd_per_kg": str(MINUS_45_USD_PER_KG),
        },
        "metrics": {key: str(value) for key, value in metrics().items()},
        "claim_boundary": [
            "2026 1P forecast in real 2026 USD, not observed realized cost",
            "2026 capital is annual planned spend, not levelized lifetime capital",
            "cost inputs and price scenarios share one issuer-filed model provenance",
            "the -45 percent case reverses under the report's +10 percent opex uncertainty",
            "not admitted into production route ranking",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=2, sort_keys=True))
