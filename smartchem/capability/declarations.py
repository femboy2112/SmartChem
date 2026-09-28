"""smartchem/capability/declarations.py -- what a declared bench SAID about each bound dimension (Round V, D10).

``ProcessBounds`` / ``PhysicalBounds`` are legacy typed leaves whose ``None`` means "unconstrained" -- and that
reading stays TRUE for every legacy caller (``evaluate_process_requirements``, the route drafter, the search
filter). The capability layer asks a DIFFERENT question: did the operator *declare* this dimension? One ``None``
cannot carry both meanings (F78: the same ``ProcessBounds`` FITS under the legacy law and is UNKNOWN under the
capability law; "no time limit" was inexpressible, so the only way to FIT was a fabricated 1e300 ceiling). So the
capability layer reads bounds ONLY through this module, and the operator's explicit "no limit" lives on the
profile (``CapabilityProfile.no_limit_dimensions``), never smuggled into a bound value.

Dimension classification (who may declare NO_LIMIT):

=====================================  ===================  =================================================
dimension                              class                NO_LIMIT allowed?
=====================================  ===================  =================================================
ProcessBounds.max_step_minutes         operator PREFERENCE  yes -- "I don't care how long a step takes"
ProcessBounds.max_total_minutes        operator PREFERENCE  yes -- patience is a preference, not a measurement
ProcessBounds.max_active_minutes       operator PREFERENCE  yes -- hands-on time the operator is willing to give
ProcessBounds.allowed_attention        operator CAPABILITY  no  -- whether someone CAN attend; a fact to declare
ProcessBounds.min_check_interval_min.  operator CAPABILITY  no  -- how often someone CAN check; declare it
ProcessBounds.allowed_agitation        operator CAPABILITY  no  -- stirring modes the bench CAN deliver
ProcessBounds.available_equipment      PHYSICAL resource    no  -- hardware exists or it does not
PhysicalBounds.max_temperature_k       PHYSICAL resource    no  -- a heat source's reach is measured, not wished
PhysicalBounds.min_pressure_atm        PHYSICAL resource    no  -- vacuum needs a pump
PhysicalBounds.max_pressure_atm        PHYSICAL resource    no  -- pressure needs a rated vessel
CapabilityProfile.budget               operator PREFERENCE  yes -- "money is no object" (budget must be None)
=====================================  ===================  =================================================

A preference can honestly be unbounded (the operator is the authority on their own patience); a capability or a
physical resource cannot -- "no limit" on a heat source or a pressure vessel is omnipotence, the exact lie Round III
D6 retired. A NO_LIMIT verdict is tagged "operator NO_LIMIT preference, not measured capability" by the assess side.
Presets NEVER emit NO_LIMIT (only an explicit caller declaration does).
"""
from __future__ import annotations

from dataclasses import fields
from enum import Enum
from typing import TYPE_CHECKING

from ..constraints import PhysicalBounds
from ..process_constraints import ProcessBounds

if TYPE_CHECKING:  # pragma: no cover - typing only (profile.py imports this module)
    from .profile import CapabilityProfile

__all__ = [
    "DimensionDeclaration",
    "NO_LIMIT_ELIGIBLE",
    "NO_LIMIT_PROCESS_ELIGIBLE",
    "BUDGET_DIMENSION",
    "PROCESS_DIMENSIONS",
    "PHYSICAL_DIMENSIONS",
    "NO_LIMIT_REASON_TAG",
    "process_dimension_state",
    "physical_dimension_state",
    "budget_state",
]


class DimensionDeclaration(str, Enum):
    """What the operator declared about ONE bound dimension."""

    UNDECLARED = "UNDECLARED"          # nothing said: a real demand on it is UNKNOWN, never a silent pass
    DECLARED_BOUND = "DECLARED_BOUND"  # a real finite bound: compare the demand against it
    NO_LIMIT = "NO_LIMIT"              # an explicit operator preference "no limit" (preference dimensions only)


#: the ProcessBounds dimensions that may be declared NO_LIMIT -- the operator-PREFERENCE time dimensions.
NO_LIMIT_PROCESS_ELIGIBLE: "frozenset[str]" = frozenset({"max_step_minutes", "max_total_minutes", "max_active_minutes"})

#: the name of the monetary preference dimension (``CapabilityProfile.budget``) in ``no_limit_dimensions``.
BUDGET_DIMENSION = "budget"

#: the ONLY dimensions that may be declared NO_LIMIT -- the operator-PREFERENCE dimensions (table above):
#: the three time preferences plus the budget (Lane G barrier amendment).
NO_LIMIT_ELIGIBLE: "frozenset[str]" = NO_LIMIT_PROCESS_ELIGIBLE | {BUDGET_DIMENSION}

#: every ProcessBounds bound dimension (schema_version is not a dimension).
PROCESS_DIMENSIONS: "frozenset[str]" = frozenset(
    f.name for f in fields(ProcessBounds) if f.name != "schema_version"
)

#: every PhysicalBounds bound dimension -- never NO_LIMIT-eligible.
PHYSICAL_DIMENSIONS: "frozenset[str]" = frozenset(
    f.name for f in fields(PhysicalBounds) if f.name != "schema_version"
)

#: the reason tag the assess side must attach to a FIT earned through a NO_LIMIT declaration.
NO_LIMIT_REASON_TAG = "operator NO_LIMIT preference, not measured capability"

if not NO_LIMIT_PROCESS_ELIGIBLE <= PROCESS_DIMENSIONS:  # pragma: no cover - import-time schema guard
    raise RuntimeError("NO_LIMIT_ELIGIBLE names a field ProcessBounds does not have")


def process_dimension_state(profile: "CapabilityProfile", field_name: str) -> DimensionDeclaration:
    """The declaration state of ``profile.process_bounds.<field_name>``.

    NO_LIMIT iff ``field_name`` is in ``profile.no_limit_dimensions`` (the profile guarantees such a field is
    eligible and carries a ``None`` bound); DECLARED_BOUND iff the ProcessBounds field is not ``None``; else
    UNDECLARED. An unknown field name is a loud error, never a silent UNDECLARED.
    """
    if field_name not in PROCESS_DIMENSIONS:
        raise ValueError(f"{field_name!r} is not a ProcessBounds dimension; known: {sorted(PROCESS_DIMENSIONS)}")
    if field_name in profile.no_limit_dimensions:
        return DimensionDeclaration.NO_LIMIT
    if getattr(profile.process_bounds, field_name) is not None:
        return DimensionDeclaration.DECLARED_BOUND
    return DimensionDeclaration.UNDECLARED


def physical_dimension_state(profile: "CapabilityProfile", field_name: str) -> DimensionDeclaration:
    """The declaration state of ``profile.physical_bounds.<field_name>``: DECLARED_BOUND or UNDECLARED only --
    a physical resource is never NO_LIMIT (see the classification table)."""
    if field_name not in PHYSICAL_DIMENSIONS:
        raise ValueError(f"{field_name!r} is not a PhysicalBounds dimension; known: {sorted(PHYSICAL_DIMENSIONS)}")
    if getattr(profile.physical_bounds, field_name) is not None:
        return DimensionDeclaration.DECLARED_BOUND
    return DimensionDeclaration.UNDECLARED


def budget_state(profile: "CapabilityProfile") -> DimensionDeclaration:
    """The declaration state of ``profile.budget``: NO_LIMIT iff ``"budget"`` is in ``no_limit_dimensions`` (the
    profile guarantees ``budget is None`` then); DECLARED_BOUND iff a ``CostVector`` ceiling is declared; else
    UNDECLARED (a real monetary demand against it is UNKNOWN, never a silent UNCONSTRAINED pass)."""
    if BUDGET_DIMENSION in profile.no_limit_dimensions:
        return DimensionDeclaration.NO_LIMIT
    if profile.budget is not None:
        return DimensionDeclaration.DECLARED_BOUND
    return DimensionDeclaration.UNDECLARED
