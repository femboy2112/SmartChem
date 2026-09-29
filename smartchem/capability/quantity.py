"""smartchem/capability/quantity.py -- the quantity-KNOWLEDGE algebra (Round V, barrier D1).

Round IV's requirement side carried ``quantity: StockQuantity | None`` and summed a group's draws with ``%g`` over
``float``: an unquantified use was silently DROPPED from the sum (F64 -- "25 mL + an unknown amount" became "25 mL"),
a mixed-unit group collapsed to ``None`` = "no gate at all" (F65 -- 10 g + 20 mL of demand FIT a 0.001 mL bottle),
and the ``%g`` / ``1e-9`` epsilon arithmetic certified 20.00004 mL out of a 20 mL bottle.

*Burp.* Here's the fix, and it's boring on purpose -- boring is what exact arithmetic looks like:

* a :class:`QuantityDemand` is NEVER ``None``. It is a per-unit-domain vector of EXACT decimal strings plus a count
  of uses the source left unquantified. Knowledge is derived, never declared: ``EXACT`` (every use stated),
  ``LOWER_BOUND_PLUS_UNKNOWN`` (some stated, some not -- the known part is only a floor), ``UNKNOWN`` (none stated,
  but the demand is still real and positive);
* units are compared by EXACT stripped string. There is no conversion engine here, no density bridge, no molar-mass
  bridge: ``"L"`` and ``"mL"`` are different domains, and ``"10 g"`` never cancels against ``"20 mL"``. Mixed units
  keep BOTH components -- nothing collapses to "no gate";
* parsing goes through the ONE strict grammar, :func:`smartchem.material_spec.exact_fraction`. No ``float()``, no
  ``%g``, no epsilon anywhere on this path.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from ..contracts import Digestible
from ..material_spec import exact_fraction

__all__ = ["QuantityKnowledge", "QuantityDemand", "fraction_to_decimal"]


class QuantityKnowledge(str, Enum):
    """How much of a requirement's whole-route demand the source actually quantifies."""

    EXACT = "EXACT"                                        # every use stated; the per-unit vector IS the demand
    LOWER_BOUND_PLUS_UNKNOWN = "LOWER_BOUND_PLUS_UNKNOWN"  # >=1 stated and >=1 unstated use: known part is a floor
    UNKNOWN = "UNKNOWN"                                    # no use stated -- demand is real and positive, size open


def fraction_to_decimal(value: Fraction) -> str:
    """Render a TERMINATING-decimal :class:`~fractions.Fraction` as its exact, canonical decimal string (no exponent,
    no trailing zeros, no float). A sum of exact decimals always terminates; anything that does not is refused."""
    if type(value) is not Fraction:
        raise TypeError("value must be a Fraction")
    if value < 0:
        raise ValueError("value must be non-negative")
    den = value.denominator
    twos = fives = 0
    while den % 2 == 0:
        den //= 2
        twos += 1
    while den % 5 == 0:
        den //= 5
        fives += 1
    if den != 1:
        raise ValueError(f"{value} is not a terminating decimal")
    places = max(twos, fives)
    scaled = value * (10 ** places)
    assert scaled.denominator == 1
    digits = str(scaled.numerator)
    if places == 0:
        return digits
    digits = digits.rjust(places + 1, "0")
    whole, frac = digits[:-places], digits[-places:].rstrip("0")
    return whole if not frac else f"{whole}.{frac}"


def _unit_key(unit: object) -> str:
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("a quantity unit must be a non-empty string")
    return unit.strip()


@dataclass(frozen=True)
class QuantityDemand(Digestible):
    """One material requirement's whole-route demand.

    ``known`` -- one ``(unit, exact decimal string)`` entry per unit domain, sorted by unit, each value > 0, stored in
    canonical decimal form (``"20.0"`` -> ``"20"``) so equal demands digest equal.
    ``unstated_uses`` -- how many uses the source left unquantified (each one a real, positive, unsized draw).

    At least one of the two must be non-empty: a requirement always stands for >= 1 use.
    """

    known: "tuple[tuple[str, str], ...]"
    unstated_uses: int

    def __post_init__(self) -> None:
        if type(self.known) is not tuple:
            raise TypeError("known must be a tuple of (unit, exact decimal string) pairs")
        canonical: "list[tuple[str, str]]" = []
        for entry in self.known:
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError("known entries must be (unit, exact decimal string) pairs")
            unit = _unit_key(entry[0])
            amount = exact_fraction(entry[1], f"quantity in {unit!r}")
            if amount <= 0:
                raise ValueError(f"a known quantity in {unit!r} must be > 0")
            canonical.append((unit, fraction_to_decimal(amount)))
        units = [u for u, _ in canonical]
        if len(units) != len(set(units)):
            raise ValueError("known may carry at most ONE entry per unit domain (sum them with combine())")
        object.__setattr__(self, "known", tuple(sorted(canonical)))
        if isinstance(self.unstated_uses, bool) or not isinstance(self.unstated_uses, int) or self.unstated_uses < 0:
            raise ValueError("unstated_uses must be a non-negative int")
        if not self.known and self.unstated_uses == 0:
            raise ValueError("a QuantityDemand stands for >= 1 use: known or unstated_uses must be non-empty")

    # -- derived views ----------------------------------------------------------------------------------------

    @property
    def knowledge(self) -> QuantityKnowledge:
        if self.unstated_uses == 0:
            return QuantityKnowledge.EXACT
        return QuantityKnowledge.LOWER_BOUND_PLUS_UNKNOWN if self.known else QuantityKnowledge.UNKNOWN

    def exact_by_unit(self) -> "dict[str, Fraction]":
        """The known per-unit components as exact :class:`~fractions.Fraction` values (never floats)."""
        return {unit: exact_fraction(value, f"quantity in {unit!r}") for unit, value in self.known}

    def render(self) -> str:
        known = " + ".join(f"{value} {unit}" for unit, value in self.known)
        if self.knowledge is QuantityKnowledge.EXACT:
            return f"EXACT {known}"
        if self.knowledge is QuantityKnowledge.LOWER_BOUND_PLUS_UNKNOWN:
            return (f"LOWER_BOUND_PLUS_UNKNOWN >= {known} plus {self.unstated_uses} unquantified use(s) -- the known "
                    "part is only a floor")
        return f"UNKNOWN ({self.unstated_uses} unquantified use(s); demand is real and positive, size unknown)"

    # -- construction -----------------------------------------------------------------------------------------

    @classmethod
    def unstated(cls, uses: int = 1) -> "QuantityDemand":
        """``uses`` real draws the source never quantified (e.g. an untyped leaf reactant)."""
        return cls((), uses)

    @classmethod
    def combine(cls, uses: "Iterable[object]") -> "QuantityDemand":
        """The commutative-monoid fold over a group's per-use quantities. Each element is a
        :class:`~smartchem.experiment.stock.StockQuantity` (anything with exact-string ``value`` and ``unit``) or
        ``None`` (an unquantified use, COUNTED -- never dropped). Same unit -> exact sum; different units -> separate
        entries (never converted, never collapsed)."""
        totals: "dict[str, Fraction]" = {}
        unstated = 0
        for use in uses:
            if use is None:
                unstated += 1
                continue
            unit = _unit_key(getattr(use, "unit", None))
            amount = exact_fraction(getattr(use, "value", None), f"quantity in {unit!r}")
            totals[unit] = totals.get(unit, Fraction(0)) + amount
        return cls(tuple((unit, fraction_to_decimal(total)) for unit, total in totals.items()), unstated)
