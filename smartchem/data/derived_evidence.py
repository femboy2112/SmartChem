"""smartchem/data/derived_evidence.py -- a minimal typed seam for DERIVED_WITH_ERROR intervals.

**Chart note.** The material library (:mod:`smartchem.data.material_library`) hands out assay/composition
intervals labelled ``DERIVED_WITH_ERROR``. Round-III's audit found that the *label* was doing all the
work: a string in the provenance said "derived", and nothing checked the arithmetic behind the number.
Two intervals were arithmetically UNSUPPORTED -- the NaCl and isoamyl-alcohol washes converted "g per
100 g water" as though it were already a mass-fraction-of-SOLUTION (263/1263 = 0.208, not the coded
band), and one band (5% +-0.5% NaHCO3) had a width with no source behind it at all -- a decorative error
bar, which project law ranks as WORSE than an honest UNKNOWN.

This module is the smallest thing that makes the calculation checkable instead of grep-able. It does NOT
rewrite the evidence subsystem; it is one frozen record that carries the exact-rational interval, the
raw inputs, and a callable that RECONSTRUCTS the interval from those inputs. The record refuses to exist
unless ``derivation_fn(*derivation_inputs) == value_interval`` (checked in ``__post_init__``) -- so a
mislabelled interval is a construction-time error, not a silent lie waiting for a reviewer to catch it.

The structural fix that would have caught the g/100g bug is the :class:`IntervalUnit` TYPE: a
``MASS_PER_100G_SOLVENT`` quantity is NOT a ``MASS_FRACTION_OF_SOLUTION`` and cannot be dropped into a
mass-fraction slot without a ``UNIT_CONVERTED`` step. The type makes the two kinds non-interchangeable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Callable


class IntervalUnit(Enum):
    """The physical TYPE of an interval's endpoints -- the distinction that catches the g/100g bug.

    A ``MASS_PER_100G_SOLVENT`` figure (g solute per 100 g of SOLVENT) is a different quantity from a
    ``MASS_FRACTION_OF_SOLUTION`` (g solute per g of SOLUTION); they coincide only in the dilute limit and
    diverge fast near saturation (35.7 g/100 g water is 0.264 of solution, not 0.357). Converting between
    them is a ``DerivationMethod.UNIT_CONVERTED`` step, never a reinterpretation of the same number.
    """

    MASS_FRACTION_OF_SOLUTION = "mass_fraction_of_solution"  # g solute / g solution, dimensionless in [0, 1]
    MASS_PER_100G_SOLVENT = "mass_per_100g_solvent"          # g solute / 100 g solvent (solubility units)
    PERCENT = "percent"                                       # a nominal percent, value in [0, 100]


class DerivationMethod(Enum):
    """How an interval was produced from its inputs -- the honest label on the arithmetic."""

    SOURCE_QUOTED = "source_quoted"   # endpoints copied straight from a cited source, no arithmetic
    UNIT_CONVERTED = "unit_converted" # endpoints produced by a units change (e.g. g/100g water -> fraction)
    CLAMPED = "clamped"               # a source range clipped to a physical bound (e.g. mass fraction <= 1.0)
    COMPLEMENT = "complement"         # the 1 - x complement of another interval (the solvent balance)
    BROADENED = "broadened"           # a nominal value widened to an honest, stated spread
    ASSUMED = "assumed"               # the width is an ASSUMED bench tolerance, NOT measured/propagated


_RationalInterval = "tuple[Fraction, Fraction]"


@dataclass(frozen=True)
class DerivedIntervalEvidence:
    """One DERIVED_WITH_ERROR interval, carried as exact rationals with its derivation attached.

    The invariant, enforced at construction: ``derivation_fn(*derivation_inputs) == value_interval``. A
    record whose stated interval does not equal what its own derivation reconstructs cannot be built. That
    is the whole point -- the old NaCl ``[0.23, 0.27]`` paired with the "26.3 g/100 g water" premise would
    raise here, because the premise reconstructs ``263/1263`` and not the coded band.
    """

    derivation_id: str
    value_interval: "tuple[Fraction, Fraction]"
    unit: IntervalUnit
    source_locator: str
    derivation_method: DerivationMethod
    derivation_inputs: "tuple[Fraction, ...]"
    derivation_fn: Callable[..., "tuple[Fraction, Fraction]"]
    domain_of_validity: str

    def __post_init__(self) -> None:
        if not isinstance(self.derivation_id, str) or not self.derivation_id.strip():
            raise ValueError("derivation_id must be a non-empty string")
        if not isinstance(self.unit, IntervalUnit):
            raise TypeError("unit must be an IntervalUnit")
        if not isinstance(self.derivation_method, DerivationMethod):
            raise TypeError("derivation_method must be a DerivationMethod")
        if not isinstance(self.source_locator, str) or not self.source_locator.strip():
            raise ValueError("source_locator must be a non-empty string")
        if not isinstance(self.domain_of_validity, str) or not self.domain_of_validity.strip():
            raise ValueError("domain_of_validity must be a non-empty string")
        lo, hi = self.value_interval
        if not isinstance(lo, Fraction) or not isinstance(hi, Fraction):
            raise TypeError("value_interval endpoints must be exact fractions.Fraction values")
        if lo > hi:
            raise ValueError("value_interval lower bound cannot exceed the upper bound")
        if any(not isinstance(x, Fraction) for x in self.derivation_inputs):
            raise TypeError("derivation_inputs must be a tuple of exact fractions.Fraction values")
        # The load-bearing check: the stated interval MUST equal what the derivation reconstructs.
        recomputed = self.recompute()
        if tuple(recomputed) != tuple(self.value_interval):
            raise ValueError(
                f"derivation mismatch for {self.derivation_id!r}: "
                f"derivation_fn(*inputs)={tuple(recomputed)} != value_interval={tuple(self.value_interval)}"
            )

    def recompute(self) -> "tuple[Fraction, Fraction]":
        """Re-run the derivation from the raw inputs -- the exact-rational interval it produces."""
        return self.derivation_fn(*self.derivation_inputs)

    def verify(self) -> bool:
        """True iff the stated interval equals what the derivation reconstructs (always True post-construction)."""
        return tuple(self.recompute()) == tuple(self.value_interval)

    def as_floats(self) -> "tuple[float, float]":
        """The interval as ``(float, float)`` for the ``MaterialComponent`` fraction slots (which take floats)."""
        lo, hi = self.value_interval
        return (float(lo), float(hi))


# -- reusable derivation kernels (pure, exact-rational) ------------------------------------------------------
# Each returns the interval from its raw inputs; each is what a record's derivation_fn points at. Keeping them
# named and shared means the same arithmetic a record claims is the arithmetic a test can re-run.


def solution_fraction_from_solubility(s_lo: Fraction, s_hi: Fraction) -> "tuple[Fraction, Fraction]":
    """g-solute-per-100 g-SOLVENT band -> mass-fraction-of-SOLUTION band, via x = s / (s + 100).

    This is the conversion the old NaCl/isoamyl intervals skipped: they used ``s`` directly as ``x``. Near
    saturation the two differ sharply (35.7 -> 0.263, not 0.357), which is exactly why the unit TYPE has to
    force this step rather than let a solubility number sit in a mass-fraction slot.
    """
    return (s_lo / (s_lo + 100), s_hi / (s_hi + 100))


def symmetric_band(nominal: Fraction, half_width: Fraction) -> "tuple[Fraction, Fraction]":
    """A nominal value +- a half-width -> ``[nominal - half_width, nominal + half_width]``.

    Honest ONLY when the record labels the method ``ASSUMED`` unless the half-width is itself sourced or
    propagated: the arithmetic is trivially correct, but a width with nothing behind it is a decorative
    error bar, which project law bans as worse than UNKNOWN.
    """
    return (nominal - half_width, nominal + half_width)


def complement_band(lo: Fraction, hi: Fraction) -> "tuple[Fraction, Fraction]":
    """The solvent balance of a solute band: ``[1 - hi, 1 - lo]`` (the low solute -> high solvent, and vice versa)."""
    return (1 - hi, 1 - lo)
