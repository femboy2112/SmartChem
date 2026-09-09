# Modern Smackover bromine undercut — bounded result (ROUND 35)

Status: **model-supported undercut at spot and spot minus 30%; the minus-45% edge is not uncertainty-robust.**

The primary source is the SEC-filed [Magnolia Field Bromine Reserves Technical Report Summary](https://www.sec.gov/Archives/edgar/data/915913/000091591326000018/ex966magnolia2025trs.htm), effective 2025-12-31 and filed 2026-02-11. It describes an operating Smackover-brine field and two processing plants. Its 2026 1P table reports 74 kt sales production, $126.0M field-and-plant operating cost, $34.7M G&A, and $27.0M capital. The same report gives a $4.89/kg spot scenario and $3.42/kg and $2.69/kg stress scenarios.

The conservative single-year cash-outflow quotient is:

`($126.0M + $34.7M + $27.0M) / 74 kt = $2.5365/kg`.

That is 48.13% below $4.89/kg and 25.83% below $3.42/kg. It is also $0.1535/kg below the report's $2.69/kg minus-45% scenario in the base model, consistent with the table's positive $11.8M 2026 cash flow before tax. However, applying the report's +10% operating-cost uncertainty only to field-and-plant opex raises the quotient to $2.7068/kg. The minus-45% edge then reverses by $0.0168/kg, while the minus-30% case retains $0.7132/kg margin.

This closes the requested modern evidence gap only at the following boundary:

- It is a 2026 forecast in real 2026 dollars, not observed realized cost.
- The numerator deliberately includes current G&A and planned 2026 capital, but that capital is not a levelized lifetime measure.
- Cost inputs are not algebraically derived from the market-price scenarios. They nevertheless share one issuer-filed model and are not independent source families.
- The RPS qualified-person report materially relies on Albemarle operating data; SEC filing is provenance and disclosure discipline, not government validation of each input.
- A separate 2024 Jordan Bromine report gives $364/t operating cost including freight to Aqaba. This is directional corroboration from a different operation, but the same issuer/reporting family and not a Magnolia substitute.
- No value from this report-only discriminator enters the production route ranker.

The executable arithmetic and source hashes are in `experiments/dow_bromine_modern_undercut_probe.py` and `experiments/dow_bromine_modern_undercut_recon_2026_09_09.json`.
