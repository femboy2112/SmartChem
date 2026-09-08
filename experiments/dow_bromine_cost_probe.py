"""DOW-BROMINE-COST-01 committed demonstration: the COST-RANKING half of the DOW-bromine litmus.

A MEASURED claim lives in a committed harness that ASSERTS, not a throwaway that prints.  This pins the
answer to "rank the two Br2 routes on cost, and reproduce why Dow undercut the German Bromkonvention
cartel" against sourced prices and against the anti-fabrication discipline (known-physics-not-new-physics).
It is a REPORT, not infrastructure: the two results are one-shot arithmetic over sourced numbers, so there
is deliberately NO importable ``smartchem`` module (a ``modern_undercut``/``historical_undercut`` API would
be imported only by its own test -- the zero-call-sites self-mirror).  Molar masses are read from the
project's sourced periodic table, never re-typed.

THEOREM 1 -- the MODERN degeneracy (a scoped honest NEGATIVE).
  The only feedstock basis we can SOURCE for the brine route today is a NaBr price derived by contained-Br
  mass fraction from the SAME bromine benchmark ``q`` the route is trying to undercut.  Its per-unit-Br2
  feedstock cost is then EXACTLY ``q`` (the mass factors cancel, algebraically, for ANY ``q``), so
  ``brine_total = q + chlorine + process >= q = mined_total`` -- strictly, once any oxidant cost is added.
  VERDICT: NO_UNDERCUT.  This is scoped: it means "no undercut is DEMONSTRABLE from the sourced same-benchmark
  proxy", NEVER "brine is worse in reality" -- real well-brine bromine (Smackover, Dead Sea) DOES undercut
  market Br2 because it carries an INDEPENDENT feedstock basis, which we simply cannot source today.  An
  undercut is certifiable ONLY on an independent, separately SOURCED feedstock price; the proxy is refused.

THEOREM 2 -- the HISTORICAL undercut (a one-sided ECONOMIC bound, route/industry level).
  The sustained multi-year USGS US bromine unit value (revenue/tonnage) is an upper bound on the US
  brine-route marginal cost: the industry produced and sold at it for years, and a whole-industry multi-year
  cross-subsidy is implausible (competitive entry/exit).  Against the cartel's administered 49 c/lb world
  price: a ~39% undercut at normal pre-war prices (USGS 1904 = 30.0 c/lb), and >= ~80% against the
  war-survival cost ceiling (USGS 1908 = 10.0 c/lb).  CAVEATS carried aloud: attribution to Dow specifically
  is a LABELLED assumption (he was a continuing US producer; the sources do NOT disclose his own cost); the
  one-sidedness is ECONOMIC and defeasible (predatory cross-subsidy is this episode's own named exception --
  NOT R30's physical law); the German dumping floor (15/12/10.5 c/lb) is the CARTEL's aggressor price, NOT
  Dow's cost, and re-export at 27 c/lb is arbitrage, not a production-cost datum.

On the "two source families": their close agreement is only at the WAR-CLEARING years (USGS 1905 = 15.0 c/lb
vs secondary dumping 15 c; USGS 1908 = 10.0 c/lb vs war floor 10.5 c) -- and that agreement is largely
COMMON-MODE, because during the war the US revenue/tonnage unit value IS the depressed clearing price the
cartel was dumping at (one market number read twice, not two independent bearings; evil-morty F2).  At the one
UNDISTORTED point the pre-war undercut rides on -- 1904 -- the families DISAGREE by ~20% (USGS 29.98 c/lb vs the
secondary US price 36 c/lb), so BOTH pre-war undercuts (~39% and ~26.5%) are reported side by side, never a
single "corroborated" figure.  Neither the price-level agreement nor its common-mode caveat touches the
price->cost step (that rests on the economic premise), and full independence-to-root is not proven.

Deterministic, tamper-pinned by a frozen digest: re-run ``python -m experiments.dow_bromine_cost_probe`` after
an INTENTIONAL change and set ``FROZEN_HASH`` to the printed value; drift reddens ``report()['hash_matches']``.

Sources (receipts: ``experiments/dow_bromine_cost_recon_2026_09_08.json``; design:
``docs/research/DOW_BROMINE_COST_RANKING_CONTRACT_v0.1.md``):
  * USGS Data Series 140, bromine historical statistics (PRIMARY, metric-tonne bromine-content unit value),
    sha256 1a4c1cf5...4258; the R16 USGS bromine benchmark ($2.70/kg contained Br, 2024).
  * Folsom, "Herbert Dow and Predatory Pricing", FEE; Mackinac Center V1997-13 (SECONDARY, cross-corroborated).
  * Los Fresnos approved municipal Cl2 offer $2.7337/kg (labelled reconnaissance -- SOURCING_RECON_2026-09-07.md).
"""
from __future__ import annotations

import hashlib
import json

from smartchem.experiment.units import molar_mass

#: The committed tamper pin.  Regenerate ONLY on an intentional change:
#: ``python -m experiments.dow_bromine_cost_probe`` and paste the printed value.
FROZEN_HASH = "11c01bb222702b703b47638bf585cb352be2ffa82e471296140db1826308c934"

# --- sourced constants --------------------------------------------------------------------------------

#: R16 USGS bromine benchmark: average unit value of imports, per unit mass of contained Br (2024 final).
Q_BROMINE_USD_PER_KG = 2.70
#: Los Fresnos approved municipal Cl2 offer, $/kg (LABELLED reconnaissance; NOT a committed default price).
CL2_RECON_USD_PER_KG = 2.733732051

#: metric tonne -> lb (USGS DS-140 header: "[All values are in metric tons (t) bromine content]").
LB_PER_TONNE = 1000.0 / 0.45359237

#: USGS DS-140 US bromine unit value, nominal $/t (bromine content).  PRIMARY.
USGS_UNIT_VALUE_USD_PER_T = {1900: 639, 1904: 661, 1905: 331, 1906: 282, 1907: 309, 1908: 220, 1909: 220}

#: SECONDARY business-history transaction prices, cents/lb (FEE / Mackinac; cross-corroborated).
CARTEL_WORLD_PRICE_CENTS_LB = 49.0            # administered/fixed world price (charged, not a mere list price)
US_PREWAR_PRICE_CENTS_LB = 36.0               # US producers (incl. Dow), pre-1904
GERMAN_DUMPING_FLOOR_CENTS_LB = (15.0, 12.0, 10.5)   # cartel AGGRESSOR price -- NOT Dow's cost
DOW_REEXPORT_CENTS_LB = 27.0                  # arbitrage (buy German @15, resell Europe) -- NOT a cost datum


def _round(x: float, n: int = 6) -> float:
    return round(float(x), n)


def _cents_per_lb(usd_per_t: float) -> float:
    """USGS nominal $/t (metric tonne, bromine content) -> cents/lb of contained Br."""
    return 100.0 * usd_per_t / LB_PER_TONNE


# --- THEOREM 1: the modern degeneracy -----------------------------------------------------------------

def modern_two_route_cost(q_usd_per_kg: float = Q_BROMINE_USD_PER_KG,
                          cl2_usd_per_kg: float = CL2_RECON_USD_PER_KG) -> dict:
    """Per-kg-Br2 cost of the two routes on the ONLY feedstock basis we can source: the same-benchmark proxy.

    ``mined`` = buy Br2 at the benchmark ``q``.  ``brine`` = NaBr feedstock (priced by contained-Br mass
    fraction from ``q``) oxidised by Cl2 (Cl2 + 2 Br- -> Br2 + 2 Cl-).  The feedstock leg is EXACTLY ``q``
    (mass factors cancel); the chlorine leg is strictly positive, so brine > mined.
    """
    m_br = molar_mass({"Br": 1})
    m_nabr = molar_mass({"Na": 1, "Br": 1})
    m_br2 = molar_mass({"Br": 2})
    m_cl2 = molar_mass({"Cl": 2})

    br_mass_fraction = m_br / m_nabr                          # contained-Br fraction of NaBr
    p_nabr_per_kg = q_usd_per_kg * br_mass_fraction           # NaBr priced purely by its Br content, at rate q
    nabr_per_kg_br2 = m_nabr / m_br                           # kg NaBr per kg Br2 (Br2 is 100% Br by mass)
    feedstock_per_kg_br2 = nabr_per_kg_br2 * p_nabr_per_kg    # == q, algebraically

    cl2_per_kg_br2 = (m_cl2 / m_br2) * cl2_usd_per_kg         # 1 mol Cl2 per mol Br2

    mined_total = q_usd_per_kg
    brine_total = feedstock_per_kg_br2 + cl2_per_kg_br2       # + rental/losses/energy (all >= 0)
    return {
        "mined_total_usd_per_kg": mined_total,
        "brine_feedstock_usd_per_kg": feedstock_per_kg_br2,   # the degeneracy: equals q
        "brine_chlorine_usd_per_kg": cl2_per_kg_br2,
        "brine_total_usd_per_kg": brine_total,
        "brine_minus_mined_usd_per_kg": brine_total - mined_total,
    }


#: The scope passport that MUST travel with the NO_UNDERCUT token wherever it is read (evil-morty F1): the
#: negative is about the sourced data, never a real-world claim that brine loses.
MODERN_VERDICT_SCOPE = "not demonstrable from the sourced same-benchmark proxy; NOT a claim that brine loses in reality"


def _is_independent_sourced_basis(basis: dict | None) -> bool:
    """The REQUIREMENT an undercut certification would have to meet: a feedstock price that is BOTH independently
    sourced (not derived from the benchmark being undercut) AND separately observed/dated/labelled.  A gate that
    opens on any handed-in value is not a gate (birdperson).  Today no such basis is sourced, so this documents
    the *unlock*, not a live computation -- the UNDERCUT branch below is structurally unreachable on the proxy
    (evil-morty F3): with only the proxy, ``brine_total`` always exceeds ``mined_total``.
    """
    return bool(basis) and basis.get("sourced") is True and basis.get("independent_of_benchmark") is True


def modern_undercut_verdict() -> dict:
    """The scoped honest NEGATIVE.  NO_UNDERCUT means 'not demonstrable from the sourced same-benchmark proxy',
    NEVER 'brine is worse in reality'.  The scope travels WITH the token (F1)."""
    cost = modern_two_route_cost()
    # The only feedstock basis we can source is the same-benchmark proxy -> fails the independence requirement,
    # AND the proxy makes brine_total > mined_total unconditionally -> the UNDERCUT branch is unreachable here
    # (a documented structural wall, not a fabricated pass).  It would open ONLY on a sourced independent basis.
    proxy_basis = {"sourced": True, "independent_of_benchmark": False, "label": "NaBr contained-Br proxy of q"}
    certifiable = _is_independent_sourced_basis(proxy_basis) and cost["brine_total_usd_per_kg"] < cost["mined_total_usd_per_kg"]
    return {
        "verdict": "UNDERCUT" if certifiable else "NO_UNDERCUT",
        "scope": MODERN_VERDICT_SCOPE,
        "brine_minus_mined_usd_per_kg": cost["brine_minus_mined_usd_per_kg"],
        "unlock": "an independent, separately sourced brine-feedstock/extraction cost (Smackover/Dead Sea well-brine)",
    }


# --- THEOREM 2: the historical one-sided economic bound -----------------------------------------------

def historical_undercut() -> dict:
    """The route/industry-level one-sided undercut bound from sourced period prices (cents/lb, inflation-neutral
    ratios of same-era prices).  Anchored on the SUSTAINED USGS unit value as an upper bound on the US
    brine-route marginal cost -- NOT on the German dumping floor, and NOT on Dow's (undisclosed) own cost."""
    cartel = CARTEL_WORLD_PRICE_CENTS_LB
    usgs_1904 = _cents_per_lb(USGS_UNIT_VALUE_USD_PER_T[1904])   # normal pre-war US unit value
    usgs_1908 = _cents_per_lb(USGS_UNIT_VALUE_USD_PER_T[1908])   # war-survival floor (industry kept producing)

    prewar_undercut_usgs = (cartel - usgs_1904) / cartel
    prewar_undercut_secondary = (cartel - US_PREWAR_PRICE_CENTS_LB) / cartel
    war_survival_lower_bound = (cartel - usgs_1908) / cartel     # cost <= 1908 unit value -> undercut >= this
    price_war_drop_1904_1905 = (USGS_UNIT_VALUE_USD_PER_T[1904] - USGS_UNIT_VALUE_USD_PER_T[1905]) / USGS_UNIT_VALUE_USD_PER_T[1904]
    return {
        "usgs_1904_cents_lb": usgs_1904,
        "usgs_1908_cents_lb": usgs_1908,
        "prewar_undercut_usgs": prewar_undercut_usgs,
        "prewar_undercut_secondary": prewar_undercut_secondary,
        "war_survival_undercut_lower_bound": war_survival_lower_bound,
        "price_war_drop_1904_to_1905": price_war_drop_1904_1905,
    }


def content_hash() -> str:
    cost = modern_two_route_cost()
    hist = historical_undercut()
    payload = {
        "mined": _round(cost["mined_total_usd_per_kg"], 6),
        "brine_feedstock": _round(cost["brine_feedstock_usd_per_kg"], 6),
        "brine_total": _round(cost["brine_total_usd_per_kg"], 6),
        "modern_verdict": modern_undercut_verdict()["verdict"],
        "modern_verdict_scope": MODERN_VERDICT_SCOPE,          # the scope travels with the token (F1)
        "usgs_1904_cents_lb": _round(hist["usgs_1904_cents_lb"], 4),
        "usgs_1908_cents_lb": _round(hist["usgs_1908_cents_lb"], 4),
        "prewar_undercut_usgs": _round(hist["prewar_undercut_usgs"], 6),
        "war_survival_lb": _round(hist["war_survival_undercut_lower_bound"], 6),
        "price_war_drop": _round(hist["price_war_drop_1904_to_1905"], 6),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold against the sourced prices and the anti-fabrication guards."""
    cost = modern_two_route_cost()

    # 1. THEOREM 1 -- the degeneracy: the same-benchmark feedstock proxy costs EXACTLY q per unit Br2.
    assert abs(cost["brine_feedstock_usd_per_kg"] - Q_BROMINE_USD_PER_KG) < 1e-9, \
        "the mass factors must cancel: feedstock proxy == q exactly"

    # 2. THEOREM 1 -- the strict inequality: any positive chlorine cost makes brine strictly costlier.
    assert cost["brine_chlorine_usd_per_kg"] > 0.0, "the oxidant leg must be strictly positive"
    assert cost["brine_total_usd_per_kg"] > cost["mined_total_usd_per_kg"], "brine > mined on the sourced proxy"

    # 3. THEOREM 1 -- the SCOPED NEGATIVE + the fail-closed certification gate.  The proxy is not an independent
    #    sourced basis, so NO_UNDERCUT is certified; an undercut is NOT (fail-closed against a fabricated pass).
    v = modern_undercut_verdict()
    assert v["verdict"] == "NO_UNDERCUT", "the sourced proxy must yield NO_UNDERCUT, never a fabricated undercut"
    assert "not demonstrable" in v["scope"] and "reality" in v["scope"], "the negative must be explicitly scoped"
    # the gate must REFUSE both an unsourced value and a non-independent (proxy) value -- it is a real gate.
    assert not _is_independent_sourced_basis(None)
    assert not _is_independent_sourced_basis({"sourced": False, "independent_of_benchmark": True})   # unsourced
    assert not _is_independent_sourced_basis({"sourced": True, "independent_of_benchmark": False})   # proxy
    assert _is_independent_sourced_basis({"sourced": True, "independent_of_benchmark": True})        # would open

    # 4. THEOREM 2 -- the USGS metric-tonne conversion + the layered one-sided bounds.
    hist = historical_undercut()
    assert abs(hist["usgs_1904_cents_lb"] - 30.0) < 0.1, "USGS 1904 unit value must be ~30.0 c/lb (metric tonne)"
    assert abs(hist["usgs_1908_cents_lb"] - 10.0) < 0.1, "USGS 1908 unit value must be ~10.0 c/lb (metric tonne)"
    assert 0.38 < hist["prewar_undercut_usgs"] < 0.40, "pre-war undercut vs 49c cartel must be ~39% (USGS 1904)"
    assert 0.26 < hist["prewar_undercut_secondary"] < 0.27, "pre-war undercut ~26.5% (secondary US 36c)"
    assert hist["war_survival_undercut_lower_bound"] > 0.79, "war-survival undercut lower bound must be >= ~80%"
    assert abs(hist["price_war_drop_1904_to_1905"] - 0.499) < 0.01, "the 1904->1905 price-war halving (~49.9%)"

    # 5. The two families agree on the PRICE LEVEL to ~1 c/lb (corroborates the price, NOT Dow's cost).
    assert abs(_cents_per_lb(USGS_UNIT_VALUE_USD_PER_T[1905]) - GERMAN_DUMPING_FLOOR_CENTS_LB[0]) < 0.5, \
        "USGS 1905 (15.0c) must match the secondary 15c dumping figure to <0.5c"
    assert abs(_cents_per_lb(USGS_UNIT_VALUE_USD_PER_T[1908]) - GERMAN_DUMPING_FLOOR_CENTS_LB[2]) < 1.0, \
        "USGS 1908 (10.0c) must match the secondary 10.5c war floor to <1c"

    # 6. ANTI-MISATTRIBUTION (birdperson): the German dumping floor is the CARTEL's aggressor price and the
    #    re-export is arbitrage -- neither is used as Dow's cost.  The cost anchor is the USGS unit value ONLY.
    assert 10.5 in GERMAN_DUMPING_FLOOR_CENTS_LB and 27.0 == DOW_REEXPORT_CENTS_LB, "context prices retained, not used as cost"


def report() -> dict:
    cost = modern_two_route_cost()
    hist = historical_undercut()
    return {
        "modern_verdict": modern_undercut_verdict()["verdict"],
        "modern_verdict_scope": MODERN_VERDICT_SCOPE,          # the token never travels without its passport (F1)
        "modern_brine_minus_mined_usd_per_kg": round(cost["brine_minus_mined_usd_per_kg"], 4),
        "historical_prewar_undercut_usgs": round(hist["prewar_undercut_usgs"], 4),
        "historical_war_survival_undercut_lower_bound": round(hist["war_survival_undercut_lower_bound"], 4),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
