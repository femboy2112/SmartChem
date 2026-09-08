"""DOW-BROMINE-COST-01: the cost-ranking half of the DOW-bromine litmus (ROUND 31).

Tests the committed harness's numbers (not a library API -- there is deliberately no importable module):
the modern degeneracy theorem + its scoped honest negative, the fail-closed certification gate, and the
one-sided historical undercut bounds re-anchored on the sourced USGS unit value.
"""
from __future__ import annotations

from experiments import dow_bromine_cost_probe as probe


def test_the_committed_demonstration_validates_and_is_frozen():
    probe.validate()                                    # raises if any sourced claim / guard fails
    r = probe.report()
    assert r["hash_matches"], f"cost demonstration drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_the_scope_travels_with_the_verdict_token():
    # evil-morty F1: the NO_UNDERCUT token must never appear without its scope passport -- in the return dict,
    # the printed report, AND the frozen hash payload (the surfaces a consumer actually reads).
    assert probe.modern_undercut_verdict()["scope"] == probe.MODERN_VERDICT_SCOPE
    assert probe.report()["modern_verdict_scope"] == probe.MODERN_VERDICT_SCOPE
    assert "not demonstrable" in probe.MODERN_VERDICT_SCOPE and "reality" in probe.MODERN_VERDICT_SCOPE


def test_modern_degeneracy_same_benchmark_proxy_costs_exactly_q():
    # THEOREM 1: a NaBr feedstock priced by contained-Br mass fraction from q costs EXACTLY q per unit Br2
    # (the mass factors cancel), so the brine route can only be >= the mined route by the oxidant cost.
    cost = probe.modern_two_route_cost()
    assert abs(cost["brine_feedstock_usd_per_kg"] - probe.Q_BROMINE_USD_PER_KG) < 1e-9
    assert cost["brine_chlorine_usd_per_kg"] > 0.0
    assert cost["brine_total_usd_per_kg"] > cost["mined_total_usd_per_kg"]


def test_modern_verdict_is_a_scoped_negative_never_a_fabricated_pass():
    v = probe.modern_undercut_verdict()
    assert v["verdict"] == "NO_UNDERCUT"
    # the negative is scoped to the sourced proxy -- NOT a claim that brine loses in reality.
    assert "not demonstrable" in v["scope"]
    assert "reality" in v["scope"]
    assert "well-brine" in v["unlock"]


def test_certification_gate_requires_an_independent_sourced_basis():
    # birdperson: a gate that opens on any handed-in value is not a gate.  It must REFUSE the same-benchmark
    # proxy AND an unsourced value, and open only on an independently-sourced basis (none exists today).
    assert not probe._is_independent_sourced_basis(None)
    assert not probe._is_independent_sourced_basis({"sourced": False, "independent_of_benchmark": True})
    assert not probe._is_independent_sourced_basis({"sourced": True, "independent_of_benchmark": False})
    assert probe._is_independent_sourced_basis({"sourced": True, "independent_of_benchmark": True})


def test_usgs_unit_value_uses_the_metric_tonne_basis():
    # the file header pins metric tonnes; the c/lb conversions only close on 2204.62 lb/t (a short-ton
    # misread would shift every figure ~10%).
    assert abs(probe._cents_per_lb(661) - 30.0) < 0.1     # USGS 1904
    assert abs(probe._cents_per_lb(220) - 10.0) < 0.1     # USGS 1908


def test_historical_undercut_is_a_one_sided_lower_bound_layered():
    h = probe.historical_undercut()
    # pre-war undercut vs the 49c cartel: ~39% (USGS 1904 30c) / ~26.5% (secondary US 36c).
    assert 0.38 < h["prewar_undercut_usgs"] < 0.40
    assert 0.26 < h["prewar_undercut_secondary"] < 0.27
    # war-survival cost ceiling (industry kept producing at ~10c) -> undercut >= ~80%.
    assert h["war_survival_undercut_lower_bound"] > 0.79
    # the price-war halving 1904->1905.
    assert abs(h["price_war_drop_1904_to_1905"] - 0.499) < 0.01


def test_family_agreement_is_common_mode_at_war_and_disagrees_when_undistorted():
    # evil-morty F2: the close ~1c agreement holds ONLY at the war-clearing years, where the USGS unit value
    # IS the depressed clearing price the cartel dumped at (common-mode -- one market number read twice).
    assert abs(probe._cents_per_lb(probe.USGS_UNIT_VALUE_USD_PER_T[1905]) - probe.GERMAN_DUMPING_FLOOR_CENTS_LB[0]) < 0.5
    assert abs(probe._cents_per_lb(probe.USGS_UNIT_VALUE_USD_PER_T[1908]) - probe.GERMAN_DUMPING_FLOOR_CENTS_LB[2]) < 1.0
    # but at the UNDISTORTED pre-war point (1904) the families DISAGREE by ~20% -- so both pre-war undercuts are
    # reported side by side, never a single "corroborated" figure.
    usgs_1904 = probe._cents_per_lb(probe.USGS_UNIT_VALUE_USD_PER_T[1904])
    assert abs(usgs_1904 - probe.US_PREWAR_PRICE_CENTS_LB) > 5.0                 # ~30 vs 36 c/lb
    h = probe.historical_undercut()
    assert h["prewar_undercut_usgs"] != h["prewar_undercut_secondary"]           # both surfaced, not merged


def test_aggressor_and_arbitrage_prices_never_move_the_cost_anchor():
    # F4 made non-vacuous: perturbing the German dumping floor and Dow's re-export must NOT change the historical
    # undercut bounds -- proving the cost anchor is the USGS unit value ONLY (anti-misattribution, birdperson).
    baseline = probe.historical_undercut()
    saved_dump, saved_reexport = probe.GERMAN_DUMPING_FLOOR_CENTS_LB, probe.DOW_REEXPORT_CENTS_LB
    try:
        probe.GERMAN_DUMPING_FLOOR_CENTS_LB = (99.0, 99.0, 99.0)                 # wild aggressor-price mutation
        probe.DOW_REEXPORT_CENTS_LB = 99.0                                       # wild re-export mutation
        assert probe.historical_undercut() == baseline, "the bound must not read the dumping/re-export figures"
    finally:
        probe.GERMAN_DUMPING_FLOOR_CENTS_LB, probe.DOW_REEXPORT_CENTS_LB = saved_dump, saved_reexport
