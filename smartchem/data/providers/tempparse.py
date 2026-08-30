"""Parse messy real-world temperature strings into a Kelvin interval -- conservatively, never guessing.

PubChem's experimental-property annotations are free text aggregated from many sources: ``"336 to 342 °F
(NTP, 1992)"``, ``"168-172"``, ``"MP: 169-170.5 °C"``, ``"117.9 °C @760 [mm Hg]"``.  This module turns that
into a single representative ``[lo, hi]`` interval in kelvin, or ``None`` when it cannot parse cleanly.  The
discipline that keeps autoload honest lives here:

* **An explicit unit is required.**  A bare number (``"168-172"``) is ambiguous and is DROPPED -- a
  stability threshold guessed from a unitless number is exactly the fabrication autoload must not commit.
* **Outliers are rejected by consensus.**  Several sourced values are aggregated by their median; values far
  from it (a wrong unit, a typo, a different polymorph) are discarded rather than widening the interval.
* **No value -> None.**  An unparseable annotation yields ``None``, which the caller renders as ``UNKNOWN``.
"""
from __future__ import annotations

import re
from statistics import median

from ...conditions import Interval

__all__ = [
    "celsius_to_k",
    "fahrenheit_to_k",
    "parse_temperature_values",
    "aggregate_kelvin",
]

_ABS_ZERO_C = 273.15
#: A number, an optional range partner, then an explicit unit (°C / C / °F / F / K).  The unit is REQUIRED.
_TEMP_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)"                        # the (first) number
    r"\s*(?:(?:to|-|–|—|~)\s*(-?\d+(?:\.\d+)?))?"  # optional range partner
    r"\s*(?:deg|°)?\s*([CFK])\b",         # an explicit unit letter (optionally after a degree sign)
    re.IGNORECASE,
)
#: Reject a parsed value whose midpoint is this far (K) from the consensus median -- a wrong-unit/typo guard.
_OUTLIER_TOLERANCE_K = 25.0


def celsius_to_k(c: float) -> float:
    return c + _ABS_ZERO_C


def fahrenheit_to_k(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0 + _ABS_ZERO_C


def _to_kelvin(value: float, unit: str) -> float:
    unit = unit.upper()
    if unit == "C":
        return celsius_to_k(value)
    if unit == "F":
        return fahrenheit_to_k(value)
    return value  # K


def parse_temperature_values(text: str) -> list[tuple[float, float]]:
    """Every unit-bearing temperature in ``text``, as ``(lo, hi)`` Kelvin intervals (a single value -> lo==hi).

    Bare unitless numbers are intentionally skipped.  Returns an empty list if nothing unit-bearing parses.
    """
    if not isinstance(text, str):
        return []
    out: list[tuple[float, float]] = []
    for m in _TEMP_RE.finditer(text):
        lo_s, hi_s, unit = m.group(1), m.group(2), m.group(3)
        try:
            lo = _to_kelvin(float(lo_s), unit)
            hi = _to_kelvin(float(hi_s), unit) if hi_s is not None else lo
        except ValueError:
            continue
        if lo > hi:
            lo, hi = hi, lo
        out.append((lo, hi))
    return out


def aggregate_kelvin(intervals: list[tuple[float, float]]) -> Interval | None:
    """Aggregate parsed Kelvin intervals into one representative :class:`Interval`, rejecting outliers.

    Uses the median midpoint as the consensus centre, keeps intervals within :data:`_OUTLIER_TOLERANCE_K` of
    it, and returns ``[min kept lo, max kept hi]``.  ``None`` if the list is empty.  This is an AGGREGATE of
    several sourced values (the provenance says so), not a single measurement dressed as exact.
    """
    if not intervals:
        return None
    mids = [(lo + hi) / 2.0 for lo, hi in intervals]
    centre = median(mids)
    kept = [iv for iv, mid in zip(intervals, mids) if abs(mid - centre) <= _OUTLIER_TOLERANCE_K]
    if not kept:  # every value is an outlier of itself only when the spread is huge; fall back to all
        kept = intervals
    return Interval(min(lo for lo, _ in kept), max(hi for _, hi in kept), "K")
