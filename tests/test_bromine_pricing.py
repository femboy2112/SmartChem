"""ROUND-16 item 2 (DOW-BROMINE-01): elemental bromine becomes a first-class SOURCED, USGS-priced commodity.

Phase 1 of the DOW-bromine litmus (predict Br2 decomposition/synthesis, rank the synthesis paths QUANTITATIVELY on
cost, reproduce why Dow's brine-bromine process undercut the German cartel).  This phase lands the COST ANCHOR: bromine
is USGS-priced (unlike the organic-price wall), so it clears the section-10.4 bar (dated AND sourced, never invented) the
same way NaCl/Na2CO3 do.  It also encodes the DOW/poor-man insight structurally -- elemental bromine is INDUSTRIAL, the
hardest availability tier, i.e. NOT a consumer/kitchen commodity: you don't BUY Br2, you MAKE it from cheap bromide.

DELIBERATELY DEFERRED (named in ROADMAP.md, not faked here): the Br2 SYNTHESIS-PATH enumeration (Cl2 + 2Br- -> Br2 +
2Cl- needs a coupled half-reaction combiner no mechanism provides today -- redox_edges is single-species charge-only;
capped_scissions ties reactant-cuts 1:1 so it cannot reach the 1:2 stoichiometry) and the brine-vs-mined COST RANKING
(blocked on a sourced Cl2 price -- chlorine hits the same aggregator wall as the organics).  Faking either would violate
section-10.4 anti-fabrication, so this round ships the sound, sourced anchor and names the two gaps.
"""
from __future__ import annotations

from smartchem.data.reagents import COMMODITY_REAGENTS, Availability, commodity_for
from smartchem.experiment import commodity_pricing as cp
from smartchem.experiment.affordability import _ACCESS_ORDINAL, basket_cost_vector
from smartchem.experiment.stock import stock_material_from_commodity

_BY_NAME = {c.name: c for c in COMMODITY_REAGENTS}
_BROMINE = _BY_NAME["bromine"].molecule


def test_bromine_carries_the_usgs_sourced_price_structure_matched():
    """The DOW litmus's cost anchor: a real dated + sourced section-10.4 observation ($2,700/t = the MCS 2026 chapter's
    2.70 $/kg bromine-content 2024 FINAL value, x1000 to the seed's $/t unit), STRUCTURE-matched to Br2 so a repointed
    'bromine' registry name would fail-SAFE to None, never borrow the price."""
    obs = cp.cost_observation_for(_BROMINE)
    assert obs is not None
    assert float(obs.amount) == 2700.0 and obs.currency == "USD" and obs.unit == "metric ton"
    assert obs.observed_date == "2024" and "USGS" in obs.source and "bromine" in obs.source
    # the per-kg origin of the number is disclosed in the source string (the x1000 is auditable, not hidden):
    assert "per kilogram of bromine content" in obs.source and "x1000" in obs.source
    # evil-morty fold: the source honestly discloses the USGS figure is a COMPOUND-DOMINATED import blend normalized to
    # contained bromine (not an elemental-Br2 spot price) -- so a reader (and the future DOW ranking phase) isn't misled.
    assert "compound-dominated" in obs.source and "not an elemental-Br2 spot price" in obs.source
    # the price binds to Br2's ACTUAL structure; a different commodity never borrows it through this path.
    assert _BY_NAME["bromine"].molecule.formula == {"Br": 2}
    assert cp.cost_observation_for(_BY_NAME["sodium chloride"].molecule).amount == "52.95"  # salt keeps its own price


def test_bromine_is_industrial_not_a_kitchen_commodity():
    """The DOW/poor-man insight encoded: elemental bromine is INDUSTRIAL -- the HARDEST availability tier, so a route
    that must BUY Br2 is not kitchen-satisfiable.  This is the honest reason Dow MADE bromine from cheap brine bromide
    rather than buying it (the synthesis ranking that will exploit this is the deferred phase 2)."""
    assert _BY_NAME["bromine"].availability is Availability.INDUSTRIAL
    assert commodity_for(_BROMINE).name == "bromine"                      # structure-resolves to the registered reagent
    v = basket_cost_vector([_BROMINE])
    assert v.cash == 2700.0                                               # the sourced price flows into the basket
    assert v.access_difficulty == _ACCESS_ORDINAL["industrial"]           # ... and it is the HARDEST tier ...
    assert v.access_difficulty == max(_ACCESS_ORDINAL.values())           # ... i.e. not consumer/kitchen-obtainable


def test_the_bromine_price_reaches_the_stock_material_bridge():
    """The live commodity->StockMaterial bridge carries the dated bromine price through, exactly as it does for salt."""
    mat = stock_material_from_commodity(_BY_NAME["bromine"])
    assert mat.cost_observation is not None
    rendered = mat.cost_observation.render()
    assert "2700.0" in rendered and "USD/metric ton" in rendered and "2024" in rendered
