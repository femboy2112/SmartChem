"""COST-VEC-01 (2a): the sourced USGS prices are wired into the material layer, honestly.

Proves the package price authority is (1) pinned to the frozen USGS seed so the two copies cannot drift, (2)
non-vacuous -- a real dated sourced section-10.4 CostObservation attaches to the priced commodities -- (3) fail-SAFE
-- an unpriced/unregistered molecule is honest UNKNOWN, never a fabricated price -- and (4) deliberate about WHICH
form it prices (the solid rock-salt bulk value, not the cheaper aqueous brine).
"""
from __future__ import annotations

from experiments.methanex_methanol_seed import METHANEX_METHANOL_PRICES
from experiments.methanex_methanol_seed import FROZEN_HASH as METHANEX_FROZEN_HASH
from experiments.methanex_methanol_seed import content_hash as methanex_content_hash
from experiments.methanex_methanol_seed import validate as validate_methanex_seed
from experiments.usgs_commodity_seed import USGS_COMMODITY_PRICES
from experiments.usgs_commodity_seed import validate as validate_seed

from smartchem.data.reagents import COMMODITY_REAGENTS
from smartchem.experiment import commodity_pricing as cp
from smartchem.experiment.stock import stock_material_from_commodity
from smartchem.smiles import parse_smiles

_BY_NAME = {c.name: c for c in COMMODITY_REAGENTS}


def test_matches_the_frozen_usgs_seed():
    """The transcription in commodity_pricing.py is byte-for-byte the frozen USGS seed -- and pins EVERY field that
    rides into the sourced observation: price AND basis AND chapter, not just the number. So a drifted or fabricated
    basis/chapter (the part of the source string that carries the section-10.4 sourcing claim) also fails here. Both
    directions, so neither a dropped form nor a drifted field can hide. Keeps the package copy honest without
    importing experiments/ at runtime."""
    validate_seed()  # the provenance seed itself is well-formed (non-vacuous, no fabricated/hollow price)
    seed = {(r.formula, r.material): (r.price_usd_per_t, r.basis, r.commodity) for r in USGS_COMMODITY_PRICES}
    mine = {(uv.formula, uv.form): (uv.price_usd_per_t, uv.basis, uv.chapter) for uv in cp._USGS_UNIT_VALUES}
    assert mine == seed


def test_priced_join_is_structure_consistent_and_forms_exist():
    """The commodity->price join binds to STRUCTURE, not just the registry name: every priced commodity's molecule
    actually carries the expected composition (so a future repoint of the name to a different structure reddens this
    AND makes cost_observation_for return None -- no borrowed price), and every priced form exists in the transcribed
    unit values (the import-time fail-fast, echoed here)."""
    for name, (formula, form, expected_counts) in cp._PRICED_COMMODITY_FORM.items():
        assert (formula, form) in cp._BY_FORM, f"{name}: priced form {(formula, form)} missing from unit values"
        assert _BY_NAME[name].molecule.formula == expected_counts, (
            f"{name}: registered molecule composition {_BY_NAME[name].molecule.formula} != expected {expected_counts}"
            " -- the name<->structure binding drifted"
        )


def test_priced_commodities_carry_a_real_dated_sourced_observation():
    """Non-vacuity: the two priced commodities each resolve to a REAL section-10.4 CostObservation -- dated, sourced,
    positive, unit-bearing. A guard that fired only over an empty set would pass while pricing nothing."""
    for name in ("sodium chloride", "sodium carbonate"):
        obs = cp.cost_observation_for(_BY_NAME[name].molecule)
        assert obs is not None, f"{name} should carry a sourced price"
        assert float(obs.amount) > 0
        assert obs.currency == "USD" and obs.unit == "metric ton"
        assert obs.observed_date and "USGS" in obs.source  # dated AND sourced (section 10.4)


def test_unpriced_or_unregistered_is_honest_unknown():
    """Fail-SAFE: a registered-but-unpriced commodity and an unregistered molecule both return None (UNKNOWN), never
    a borrowed or invented number."""
    assert cp.cost_observation_for(_BY_NAME["ethanol"].molecule) is None  # registered, no sourced price
    assert cp.cost_observation_for(parse_smiles("CCCCCCCCO")) is None      # octan-1-ol: not a commodity at all


def test_matches_the_frozen_methanex_seed():
    """COST-VEC-01 ROUND-14: the METHANOL organic price transcribed into commodity_pricing.py is byte-for-byte the
    frozen Methanex seed, which is itself well-formed and hash-pinned -- so the two copies cannot drift and a fabricated
    number/basis cannot slip in.  The Methanex source is DISTINCT from USGS (a producer's posted reference), so it gets
    its own seed + cross-check, exactly as the USGS copy does."""
    validate_methanex_seed()                                   # the provenance seed is well-formed (non-vacuous)
    assert methanex_content_hash() == METHANEX_FROZEN_HASH     # tamper pin: the frozen set has not drifted
    seed = METHANEX_METHANOL_PRICES[0]
    assert seed.commodity == "methanol" and seed.region == "North America"
    # the package transcription equals the seed value (the drift guard, both the number AND the sourcing basis).
    assert float(cp._METHANEX_METHANOL_USD_PER_T) == seed.price_usd_per_t
    assert seed.posted_date == cp._METHANEX_OBSERVED_DATE
    assert "Non-Discounted Reference Price" in cp._METHANEX_SOURCE and "not retail" in cp._METHANEX_SOURCE


def test_methanol_carries_the_methanex_sourced_organic_price_structure_matched():
    """The FIRST sourced ORGANIC price lights up the cash floor for methanol: a real dated + sourced section-10.4
    observation (lifting the USGS seed's 'no organic acid' boundary for methanol), and it is STRUCTURE-matched so a
    repointed 'methanol' registry name yields None, never a borrowed price (the same fail-SAFE join the USGS path has)."""
    obs = cp.cost_observation_for(_BY_NAME["methanol"].molecule)
    assert obs is not None                                     # methanol is now priced (organic-price block lifted)
    assert float(obs.amount) == 1414.0 and obs.currency == "USD" and obs.unit == "metric ton"
    assert obs.observed_date == "2026-08-28" and "Methanex" in obs.source   # dated AND sourced (section 10.4)
    assert obs.region == "North America"
    # the price binds to methanol's ACTUAL structure (CH4O): the registry entry carries exactly that composition, so
    # the join holds; the `commodity.molecule.formula == _METHANOL_COUNTS` guard would fail-SAFE to None on a repoint.
    assert _BY_NAME["methanol"].molecule.formula == cp._METHANOL_COUNTS
    # and a different registered commodity (ethanol) never borrows methanol's price through this path.
    assert cp.cost_observation_for(_BY_NAME["ethanol"].molecule) is None


def test_prices_the_named_solid_form_not_the_cheaper_brine():
    """The sodium-chloride price is the rock-salt SOLID bulk value (52.95 $/t), not the numerically cheaper aqueous
    'salt in brine' (10.56 $/t) -- an auto-min would misattribute a solution's price to a solid reagent. The brine
    value is still in the transcription (so the seed cross-check is complete); it is deliberately not the attached
    price."""
    obs = cp.cost_observation_for(_BY_NAME["sodium chloride"].molecule)
    assert obs.amount == "52.95"
    assert "rock salt" in obs.source and "brine" not in obs.source
    assert any(uv.form == "salt in brine" and uv.price_usd_per_t == 10.56 for uv in cp._USGS_UNIT_VALUES)


def test_stock_bridge_attaches_the_price_and_renders_it():
    """The live commodity->StockMaterial bridge carries the dated price through, and an unpriced commodity's material
    still reads honest UNKNOWN."""
    mat = stock_material_from_commodity(_BY_NAME["sodium chloride"])
    assert mat.cost_observation is not None
    rendered = mat.cost_observation.render()
    assert "52.95" in rendered and "USD/metric ton" in rendered and "2024" in rendered

    unpriced = stock_material_from_commodity(_BY_NAME["ethanol"])
    assert unpriced.cost_observation is None
