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
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass

from .contracts import Digestible

__all__ = ["PHYSICAL_BOUNDS_SCHEMA", "PhysicalBounds"]

PHYSICAL_BOUNDS_SCHEMA = "smartchem.constraints/physical-bounds-v1alpha1"

_BOUND_NAMES = ("max_temperature_k", "min_pressure_atm", "max_pressure_atm")


@dataclass(frozen=True)
class PhysicalBounds(Digestible):
    """A section-11 temperature/pressure constraint: each bound is a positive, finite value or ``None``.

    ``None`` on a bound means that dimension is UNCONSTRAINED.  An all-``None`` box constrains nothing -- a route
    judged against it is ``UNCONSTRAINED`` (nothing assessed), never a pass (section 11).  Validation is strict
    (CONSTR-VAL-01): a bound must be a real, finite, positive number, and ``min_pressure_atm`` may not exceed
    ``max_pressure_atm`` (an empty pressure window).
    """

    schema_version: str = PHYSICAL_BOUNDS_SCHEMA
    max_temperature_k: "float | None" = None
    min_pressure_atm: "float | None" = None
    max_pressure_atm: "float | None" = None

    def __post_init__(self) -> None:
        if self.schema_version != PHYSICAL_BOUNDS_SCHEMA:
            raise ValueError(f"schema_version must be exactly {PHYSICAL_BOUNDS_SCHEMA!r}")
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

    @classmethod
    def of(
        cls,
        *,
        max_temperature_k: "float | None" = None,
        min_pressure_atm: "float | None" = None,
        max_pressure_atm: "float | None" = None,
    ) -> "PhysicalBounds":
        """Build a bounds box from keyword bounds (the ``schema_version`` is supplied)."""
        return cls(PHYSICAL_BOUNDS_SCHEMA, max_temperature_k, min_pressure_atm, max_pressure_atm)

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
        if self.max_temperature_k is not None:
            parts.append(f"T<={self.max_temperature_k:g} K")
        if self.min_pressure_atm is not None:
            parts.append(f"P>={self.min_pressure_atm:g} atm")
        if self.max_pressure_atm is not None:
            parts.append(f"P<={self.max_pressure_atm:g} atm")
        return ", ".join(parts) if parts else "unconstrained"
