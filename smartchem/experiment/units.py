"""TERM-MAT-01 (Lane C): the molar-mass + price-unit-conversion layer -- the two DERIVATIONS that turn a per-package
price and a stoichiometric mol requirement into a quantity-weighted cash, and a gram amount into moles (SHOP-LEAF).

Two conversions, both KNOWN physics (sourced constants / definitional unit factors), never fabricated:

* :func:`molar_mass` -- grams per mole of a composition, summed from the SOURCED IUPAC/CIAAW standard atomic weights
  in :mod:`smartchem.data.periodic_table`.  Honest ``None`` (UNKNOWN, never a fabricated mass) if ANY element lacks a
  *real* standard atomic weight (the naturally-radioactive / synthetic elements whose tabulated value is only a
  most-stable-isotope mass number -- ``has_standard_atomic_weight`` is False for them; a mass number is not a molar
  mass and must not masquerade as one).
* :func:`grams_per_unit` -- grams in one price/amount denominator.  ONLY mass units convert: the factors are exact
  DEFINITIONS (the SI tonne, the 1959 international avoirdupois pound), not measurements.  A volume ("L"), a count
  ("each"), or any unrecognised denominator returns ``None`` -- you cannot honestly turn a per-litre or per-piece
  price into a per-gram one without a density or a package mass this layer does not have (a NAMED boundary, never a
  guessed factor).

Built on those: :func:`price_per_gram` / :func:`price_per_mol` convert a section-10.4 :class:`~smartchem.experiment.
stock.CostObservation` (a dated, sourced price with a ``unit`` denominator) into a per-gram / per-mol price, and
:func:`grams_to_moles` / :func:`moles_to_grams` are the SHOP-LEAF gram<->mol bridge.  Every one fails to ``None``
(UNKNOWN) rather than inventing a factor when the denominator is not a mass unit or the composition has no molar mass.

Boundary (named, not hidden): :func:`molar_mass` returns a POINT value to the 4-5 significant figures of the abridged
standard atomic weights; it does NOT propagate the (tiny) atomic-weight uncertainty -- far below the uncertainty of
any price or yield it multiplies, so a point mass is the honest scope here (a molar-mass sigma is a documented
follow-on, orthogonal to the cash it weights).  These conversions are BASIS-only: they never assay a commodity (a
priced commodity is still an UNKNOWN-assay lead per TERM-MAT-01), so a quantity-weighted cash built on them is a
LOWER BOUND, not an exact total -- the caller labels it as such.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from ..data.periodic_table import has_standard_atomic_weight, standard_atomic_weight

__all__ = [
    "MASS_UNIT_GRAMS",
    "MASS_UNIT_SOURCE",
    "grams_per_unit",
    "molar_mass",
    "price_per_gram",
    "price_per_mol",
    "grams_to_moles",
    "moles_to_grams",
]

#: The provenance of the mass-unit factors below -- exact DEFINITIONS, not measurements.
MASS_UNIT_SOURCE = (
    "SI (the tonne = 1e3 kg, BIPM SI Brochure) and the 1959 International Yard and Pound Agreement "
    "(1 avoirdupois pound = 0.45359237 kg exactly); all factors are definitional, not measured"
)

#: grams in one of each recognised MASS unit.  Keys are the normalised (lowercased, stripped) denominator strings a
#: price/amount can carry.  Every value is EXACT by definition (see :data:`MASS_UNIT_SOURCE`).  A denominator absent
#: here (a volume, a count, an unrecognised word) is UNKNOWN -- :func:`grams_per_unit` returns None, never a guess.
MASS_UNIT_GRAMS: "dict[str, float]" = {
    # SI, exact
    "metric ton": 1_000_000.0,
    "metric tonne": 1_000_000.0,
    "tonne": 1_000_000.0,
    "t": 1_000_000.0,
    "kg": 1_000.0,
    "kilogram": 1_000.0,
    "kilograms": 1_000.0,
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "mg": 1e-3,
    "milligram": 1e-3,
    "ug": 1e-6,
    "microgram": 1e-6,
    # avoirdupois, exact via the 1959 international pound
    "lb": 453.59237,
    "pound": 453.59237,
    "pounds": 453.59237,
    "oz": 28.349523125,          # 1/16 lb, exact
    "ounce": 28.349523125,
    "short ton": 907_184.74,     # 2000 lb (US), exact
    "long ton": 1_016_046.9088,  # 2240 lb (UK/imperial), exact
}


def grams_per_unit(unit: str) -> "float | None":
    """Grams in one ``unit`` of a price/amount denominator, or ``None`` (UNKNOWN) for a non-mass unit.

    Normalises case and surrounding whitespace only -- it does NOT guess at abbreviations it does not know (``"mt"``
    is deliberately absent: it is ambiguous between metric ton and megatonne, so it fails to UNKNOWN rather than
    pick one).  A volume ("L", "mL"), a count ("each", "unit"), or any unrecognised word returns ``None``: converting
    those to grams needs a density or a package mass this layer does not have (the named boundary)."""
    if not isinstance(unit, str):
        return None
    return MASS_UNIT_GRAMS.get(unit.strip().lower())


def _counts(composition: "Mapping[str, int] | Iterable[tuple[str, int]]") -> "list[tuple[str, int]]":
    """Normalise a composition (a symbol->count mapping, or an iterable of (symbol, count) pairs) to a pair list."""
    if isinstance(composition, Mapping):
        return list(composition.items())
    return list(composition)


def molar_mass(composition: "Mapping[str, int] | Iterable[tuple[str, int]]") -> "float | None":
    """Grams per mole of ``composition`` (a ``{symbol: count}`` mapping or ``(symbol, count)`` pairs), or ``None``.

    Summed from the SOURCED IUPAC/CIAAW standard atomic weights (u == g/mol numerically).  Returns ``None`` (honest
    UNKNOWN) if ANY element lacks a *real* standard atomic weight -- a naturally-radioactive or synthetic element
    whose tabulated value is only a most-stable-isotope mass number is NOT a molar mass, so a composition containing
    one has no honest molar mass rather than a fabricated one.  An empty composition (no atoms) is also ``None``."""
    pairs = _counts(composition)
    if not pairs:
        return None
    total = 0.0
    for symbol, count in pairs:
        if not isinstance(count, (int, float)) or isinstance(count, bool) or count <= 0:
            return None  # a non-positive / non-numeric count is not an honest composition -> UNKNOWN
        if not has_standard_atomic_weight(symbol):
            return None  # unknown symbol, or a mass-number-only radioactive/synthetic element -> no molar mass
        total += standard_atomic_weight(symbol) * count
    return total


def price_per_gram(observation: "object") -> "tuple[float, str] | None":
    """Convert a :class:`~smartchem.experiment.stock.CostObservation` to ``(price_per_gram, currency)``, or ``None``.

    ``None`` (UNKNOWN, never a fabricated conversion) when the observation's ``unit`` denominator is not a MASS unit
    (a per-litre or per-piece price has no per-gram value without a density/package mass) or its amount is
    unparseable.  The currency is passed through unchanged -- this converts the DENOMINATOR, never the numeraire."""
    amount = getattr(observation, "amount", None)
    unit = getattr(observation, "unit", None)
    currency = getattr(observation, "currency", None)
    if amount is None or unit is None or not isinstance(currency, str) or not currency:
        return None
    grams = grams_per_unit(unit)
    if grams is None or grams <= 0:
        return None
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    if value != value or value < 0:  # NaN / negative price -> not an honest price
        return None
    return value / grams, currency


def price_per_mol(
    observation: "object", composition: "Mapping[str, int] | Iterable[tuple[str, int]]"
) -> "tuple[float, str] | None":
    """Convert a :class:`~smartchem.experiment.stock.CostObservation` to ``(price_per_mol, currency)``, or ``None``.

    ``price_per_gram`` times the composition's :func:`molar_mass`; ``None`` (UNKNOWN) if EITHER is unknown -- a
    non-mass denominator OR a composition with no honest molar mass leaves the per-mol price honestly UNKNOWN."""
    per_gram = price_per_gram(observation)
    if per_gram is None:
        return None
    mm = molar_mass(composition)
    if mm is None or mm <= 0:
        return None
    value, currency = per_gram
    return value * mm, currency


def grams_to_moles(
    grams: float, composition: "Mapping[str, int] | Iterable[tuple[str, int]]"
) -> "float | None":
    """Moles in ``grams`` of ``composition`` (the SHOP-LEAF gram->mol bridge), or ``None`` if the molar mass is
    unknown / the input is not a finite non-negative mass."""
    if not isinstance(grams, (int, float)) or isinstance(grams, bool) or grams != grams or grams < 0:
        return None
    mm = molar_mass(composition)
    if mm is None or mm <= 0:
        return None
    return grams / mm


def moles_to_grams(
    moles: float, composition: "Mapping[str, int] | Iterable[tuple[str, int]]"
) -> "float | None":
    """Grams in ``moles`` of ``composition`` (the mol->gram bridge), or ``None`` if the molar mass is unknown / the
    input is not a finite non-negative amount."""
    if not isinstance(moles, (int, float)) or isinstance(moles, bool) or moles != moles or moles < 0:
        return None
    mm = molar_mass(composition)
    if mm is None or mm <= 0:
        return None
    return moles * mm
