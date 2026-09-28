"""The one section-11 PHYSICAL constraint leaf (CLI-CAN-02): temperature and pressure bounds.

Before this, the section-11 T/P bounds lived only inside :class:`~smartchem.experiment.drafter.ConstraintBox`, a
HIGH module that imports the whole experiment subsystem (accounting, ceiling, composability, ...).  The typed
compilation service (:mod:`smartchem.service`) could not carry a real constraint without either importing that
whole stack (a layering regression) or growing a SECOND T/P model with its own validation (the duplicate-model
hazard the "one parser" discipline forbids).

``PhysicalBounds`` is the shared leaf that resolves both: a pure, digestible value (it imports only
:mod:`smartchem.contracts` plus the stdlib), so the service's :class:`~smartchem.service.ConstraintPolicy` carries
it directly, and ``ConstraintBox`` DELEGATES its T/P validation here -- so the finite/positive/ordered rules
(CONSTR-VAL-01) live in exactly ONE place.  It models temperature and pressure only; the bench's reagent and
equipment inventory stay with ``ConstraintBox`` (the request already carries reagents/stock in its own fields).

Round V X-high (barrier D14, F-1): temperature is a RANGE, not a ceiling.  ``v1alpha1`` could say "this bench cannot
exceed 500 K" but not "this bench cannot get below 250 K", so an ice-bath or cryogenic demand had no honest capability
coordinate and a 77 K cooling step certified against a kitchen.  ``v1alpha2`` appends ``min_temperature_k`` (LAST --
two positional call sites) to THIS leaf rather than growing a second, capability-only temperature model: route demand
and bench capability stay one type.  The legacy reading is untouched -- ``None`` still means UNCONSTRAINED for every
legacy caller -- and a ``v1alpha1`` box is still constructible (a released v0.8 payload decodes to one) ONLY with the
floor left ``None``: a v1alpha1 record never said anything about a lower temperature, so it may not carry one.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass

from .contracts import Digestible

__all__ = ["PHYSICAL_BOUNDS_SCHEMA", "PHYSICAL_BOUNDS_SCHEMA_V1", "PhysicalBounds"]

PHYSICAL_BOUNDS_SCHEMA = "smartchem.constraints/physical-bounds-v1alpha2"
#: The released v0.8 shape (no temperature floor). Accepted ONLY with ``min_temperature_k is None`` (legacy decode).
PHYSICAL_BOUNDS_SCHEMA_V1 = "smartchem.constraints/physical-bounds-v1alpha1"
_ACCEPTED_SCHEMAS = (PHYSICAL_BOUNDS_SCHEMA, PHYSICAL_BOUNDS_SCHEMA_V1)

_BOUND_NAMES = ("max_temperature_k", "min_pressure_atm", "max_pressure_atm", "min_temperature_k")


@dataclass(frozen=True)
class PhysicalBounds(Digestible):
    """A section-11 temperature/pressure constraint: each bound is a positive, finite value or ``None``.

    ``None`` on a bound means that dimension is UNCONSTRAINED.  An all-``None`` box constrains nothing -- a route
    judged against it is ``UNCONSTRAINED`` (nothing assessed), never a pass (section 11).  Validation is strict
    (CONSTR-VAL-01): a bound must be a real, finite, positive number, ``min_pressure_atm`` may not exceed
    ``max_pressure_atm`` (an empty pressure window), and ``min_temperature_k`` may not exceed ``max_temperature_k``
    (an empty temperature window).

    ``min_temperature_k`` (D14) is the lowest temperature: on a route DEMAND, the coldest a step must be taken; on a
    bench CAPABILITY, the coldest the bench can reach.  It is appended LAST so positional construction is unchanged.
    """

    schema_version: str = PHYSICAL_BOUNDS_SCHEMA
    max_temperature_k: "float | None" = None
    min_pressure_atm: "float | None" = None
    max_pressure_atm: "float | None" = None
    min_temperature_k: "float | None" = None

    def __post_init__(self) -> None:
        if self.schema_version not in _ACCEPTED_SCHEMAS:
            raise ValueError(f"schema_version must be exactly {PHYSICAL_BOUNDS_SCHEMA!r} "
                             f"(or the legacy {PHYSICAL_BOUNDS_SCHEMA_V1!r})")
        if self.schema_version == PHYSICAL_BOUNDS_SCHEMA_V1 and self.min_temperature_k is not None:
            raise ValueError(f"a legacy {PHYSICAL_BOUNDS_SCHEMA_V1!r} box has no temperature floor -- "
                             f"min_temperature_k needs {PHYSICAL_BOUNDS_SCHEMA!r}")
        for name in _BOUND_NAMES:
            v = getattr(self, name)
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, numbers.Real):
                raise TypeError(f"{name} must be a real number or None")
            if not math.isfinite(float(v)) or v <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if (
            self.min_pressure_atm is not None
            and self.max_pressure_atm is not None
            and self.min_pressure_atm > self.max_pressure_atm
        ):
            raise ValueError("min_pressure_atm cannot exceed max_pressure_atm")
        if (
            self.min_temperature_k is not None
            and self.max_temperature_k is not None
            and self.min_temperature_k > self.max_temperature_k
        ):
            raise ValueError("min_temperature_k cannot exceed max_temperature_k")

    @classmethod
    def of(
        cls,
        *,
        max_temperature_k: "float | None" = None,
        min_pressure_atm: "float | None" = None,
        max_pressure_atm: "float | None" = None,
        min_temperature_k: "float | None" = None,
    ) -> "PhysicalBounds":
        """Build a bounds box from keyword bounds (the current ``schema_version`` is supplied)."""
        return cls(PHYSICAL_BOUNDS_SCHEMA, max_temperature_k, min_pressure_atm, max_pressure_atm, min_temperature_k)

    @classmethod
    def unconstrained(cls) -> "PhysicalBounds":
        """The all-``None`` box: constrains nothing."""
        return cls()

    @property
    def constrains_anything(self) -> bool:
        """True iff at least one bound is declared."""
        return any(getattr(self, name) is not None for name in _BOUND_NAMES)

    def describe(self) -> str:
        """A short human description of the declared bounds, or ``'unconstrained'`` when nothing is declared."""
        parts = []
        if self.min_temperature_k is not None:
            parts.append(f"T>={self.min_temperature_k:g} K")
        if self.max_temperature_k is not None:
            parts.append(f"T<={self.max_temperature_k:g} K")
        if self.min_pressure_atm is not None:
            parts.append(f"P>={self.min_pressure_atm:g} atm")
        if self.max_pressure_atm is not None:
            parts.append(f"P<={self.max_pressure_atm:g} atm")
        return ", ".join(parts) if parts else "unconstrained"
