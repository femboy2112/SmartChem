"""COST-VEC-01: dated, sourced commodity prices wired into the compiler's material layer.

The frozen ``experiments/usgs_commodity_seed.py`` (USGS Mineral Commodity Summaries 2026, read off the primary
chapter PDFs, item 5) is the PROVENANCE artifact.  This module is the package-resident price authority the runtime
uses -- the package cannot import from ``experiments/`` (it is not part of the installed package), so the load-bearing
numbers are transcribed here and pinned to the seed by
``tests/test_commodity_pricing.py::test_matches_the_frozen_usgs_seed``: a drift between the two fails that test, so
the two copies cannot diverge (the same discipline ``data/thermo.SEED_THERMO_REFS`` keeps against the CODATA seed).  The cross-check pins EVERY
transcribed field that rides into the sourced observation -- formula, form, price, basis, and chapter -- not just the
number, so a drifted or fabricated *basis/chapter* (the part of the ``source`` string that carries the sourcing
claim) also fails the test.

Every price becomes a section-10.4 :class:`~smartchem.experiment.stock.CostObservation` -- dated AND sourced, never
invented (section 10.4 forbids a fabricated price).  A priced commodity is mapped to a SPECIFIC USGS form (not the
numeric minimum across forms: the cheapest "NaCl" unit value is brine at 10.56 $/t, an aqueous solution, not the
solid reagent the commodity is -- an auto-min would misattribute a solution's price to a solid).  The chosen form is
named in the observation's ``source`` so it can never be mistaken for a retail price; it is a bulk wholesale unit
value.  Only a commodity whose identity already has a registered ``CommodityReagent`` is priced here; a priced form
with no registry entry (lime, sulfur) is transcribed for provenance but NOT attached -- adding a new commodity to
the retrosynthesis inventory is a separate, behaviour-affecting change, out of scope for this price-wiring brick.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule
from .stock import CostObservation

#: The USGS edition + the FINAL (non-estimated) year its unit values are for; the observation date is that year.
SOURCE = "USGS Mineral Commodity Summaries 2026 (U.S. Geological Survey, February 2026)"
OBSERVED_DATE = "2024"  # the most recent FINAL (non-estimated) average-unit-value year in the MCS 2026 edition
CURRENCY = "USD"
UNIT = "metric ton"


@dataclass(frozen=True)
class _UnitValue:
    """One USGS 2024 FINAL average unit value ($/metric ton) for a bulk commodity form (transcribed from the seed)."""

    formula: str
    form: str
    price_usd_per_t: float
    basis: str
    chapter: str


# Transcribed from experiments/usgs_commodity_seed.py::USGS_COMMODITY_PRICES (2024 FINAL $/t).  Cross-checked live
# against the frozen seed -- do NOT edit a number here without re-reading the dated source and updating the seed.
_USGS_UNIT_VALUES: tuple[_UnitValue, ...] = (
    _UnitValue("NaCl", "rock salt", 52.95,
               "average unit value of bulk, pellets and packaged salt, f.o.b. mine and plant", "salt"),
    _UnitValue("NaCl", "solar salt", 152.87,
               "average unit value of bulk, pellets and packaged salt, f.o.b. mine and plant", "salt"),
    _UnitValue("NaCl", "vacuum and open pan salt", 259.69,
               "average unit value of bulk, pellets and packaged salt, f.o.b. mine and plant", "salt"),
    _UnitValue("NaCl", "salt in brine", 10.56,
               "average unit value of bulk, pellets and packaged salt, f.o.b. mine and plant", "salt"),
    _UnitValue("Na2CO3", "soda ash (natural)", 169.35,
               "average unit value of sales (natural source), f.o.b. mine or plant", "soda ash"),
    _UnitValue("CaO", "quicklime", 261.4, "average value at plant", "lime"),
    _UnitValue("Ca(OH)2", "hydrated lime", 274.2, "average value at plant", "lime"),
    _UnitValue("S", "elemental sulfur", 46.42,
               "average unit value, f.o.b. mine and (or) plant, per metric ton of elemental sulfur", "sulfur"),
)

#: A registered commodity (by its registry name -- a structure-matched `commodity_for` result selects it) -> the
#: SPECIFIC USGS ``(formula, form, expected element composition)`` whose unit value represents it.  Deliberately
#: explicit, not an auto-min across incomparable forms.  The expected composition is verified against the matched
#: molecule at lookup, so the price binds to STRUCTURE, not merely the registry name (repointing the name to a
#: different structure yields None, never a borrowed price).  Extend this only alongside a registered
#: CommodityReagent for the identity.
_PRICED_COMMODITY_FORM: dict[str, tuple[str, str, dict[str, int]]] = {
    "sodium chloride": ("NaCl", "rock salt", {"Na": 1, "Cl": 1}),
    "sodium carbonate": ("Na2CO3", "soda ash (natural)", {"Na": 2, "C": 1, "O": 3}),
}

_BY_FORM: dict[tuple[str, str], _UnitValue] = {(uv.formula, uv.form): uv for uv in _USGS_UNIT_VALUES}

# Fail-fast at import: every priced form must exist in the transcribed unit values, so a typo'd form is caught here
# rather than as an uncaught KeyError in the live bridge path.
for _name, (_formula, _form, _counts) in _PRICED_COMMODITY_FORM.items():
    if (_formula, _form) not in _BY_FORM:
        raise ValueError(
            f"priced commodity {_name!r} names USGS form {(_formula, _form)!r} absent from _USGS_UNIT_VALUES"
        )


def _observation(uv: _UnitValue) -> CostObservation:
    return CostObservation.of(
        f"{uv.price_usd_per_t}", CURRENCY, UNIT, OBSERVED_DATE,
        f"{SOURCE}, {uv.chapter} chapter, {uv.form} ({uv.basis}) -- bulk wholesale unit value, not retail",
    )


# -- the Methanex organic price (COST-VEC-01, ROUND-14): methanol, the FIRST sourced ORGANIC commodity price ---------
# A DISTINCT source from USGS (a PRODUCER'S posted reference, not a government average unit value), transcribed from
# the frozen ``experiments/methanex_methanol_seed.py`` and cross-checked by
# ``tests/test_commodity_pricing.py::test_matches_the_frozen_methanex_seed`` (the same drift-proof discipline the USGS
# copy uses).  It lifts the USGS seed's "USGS prices no organic acid" boundary for METHANOL ONLY; every other organic
# stays UNPRICED (fail-SAFE None), never a borrowed or fabricated number.
_METHANEX_METHANOL_USD_PER_T = "1414"     # North America, Aug 28 2026 sheet -- matches the frozen seed's 1414.0
_METHANEX_OBSERVED_DATE = "2026-08-28"    # the sheet's posting date (effective Sep 1-30, 2026)
_METHANEX_SOURCE = (
    "Methanex Methanol Price Sheet (Aug 28, 2026), North America Non-Discounted Reference Price (valid Sep 1-30, "
    "2026) -- a producer's posted bulk reference price, not retail"
)
_METHANOL_COUNTS = {"C": 1, "H": 4, "O": 1}   # the structure the price binds to (a repointed name yields None)


def _methanex_methanol_observation() -> CostObservation:
    return CostObservation.of(
        _METHANEX_METHANOL_USD_PER_T, CURRENCY, UNIT, _METHANEX_OBSERVED_DATE, _METHANEX_SOURCE, region="North America",
    )


def cost_observation_for(molecule: Molecule) -> "CostObservation | None":
    """The dated, sourced section-10.4 price for a commodity ``molecule``, or ``None`` (honest UNKNOWN) if none.

    Keyed by the canonical-structure-matched commodity (``data.reagents.commodity_for``), so a same-formula isomer can
    never borrow a price; then the explicit :data:`_PRICED_COMMODITY_FORM` selects the representative USGS form.  A
    registered commodity with no priced form (or an unregistered molecule) returns ``None`` -- fail-SAFE (a missing
    price is UNKNOWN, never a fabricated number)."""
    from ..data.reagents import commodity_for  # forward dep (data<-experiment); at call time to keep import light

    commodity = commodity_for(molecule)
    if commodity is None:
        return None
    priced = _PRICED_COMMODITY_FORM.get(commodity.name)
    if priced is not None:
        formula, form, expected_counts = priced
        # structure-sound the join: the matched commodity's molecule must actually carry the priced form's composition,
        # so repointing the registry NAME to a different structure yields None (fail-SAFE), never a borrowed price.
        if commodity.molecule.formula != expected_counts:  # `formula` is a property (dict), not a method
            return None
        return _observation(_BY_FORM[(formula, form)])
    # ROUND-14: the Methanex organic price (methanol), a DISTINCT source from the USGS forms above.  Structure-matched
    # the SAME way -- methanol's CH4O composition must hold, so a repointed "methanol" name yields None, never a price.
    if commodity.name == "methanol" and commodity.molecule.formula == _METHANOL_COUNTS:
        return _methanex_methanol_observation()
    return None
