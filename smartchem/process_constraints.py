"""Declared process requirements and operator-resource constraints.

This layer compares supplied facts.  It does not infer work, attention, agitation,
equipment or feasibility from temperature, a formula, or a reaction name.  ``FITS``
means only that the declared requirements fit the selected dimensions; it neither
validates chemistry nor converts a reviewed citation into a validated procedure.

The quick and low-touch presets are editable software preference examples, not
chemical thresholds or recommendations about unattended reactions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from .contracts import Digestible
from .provenance import SourceCitation

if TYPE_CHECKING:
    from .conditions import ConditionEnvelope, Interval

__all__ = [
    "PROCESS_BOUNDS_SCHEMA", "Attention", "Agitation", "ProcessRequirements",
    "ProcessBounds", "ProcessFitStatus", "ProcessFit", "evaluate_process",
]

PROCESS_BOUNDS_SCHEMA = "smartchem.constraints/process-bounds-v1alpha1"


class Attention(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    PERIODIC = "PERIODIC"
    PASSIVE = "PASSIVE"


class Agitation(str, Enum):
    NONE = "NONE"
    MANUAL = "MANUAL"
    PERIODIC = "PERIODIC"
    CONTINUOUS = "CONTINUOUS"


def _number(record: object, name: str, *, positive: bool = False) -> None:
    value = getattr(record, name)
    if value is None:
        return
    if isinstance(value, bool) or type(value) not in (int, float):
        raise TypeError(f"{name} must be a real number or None")
    try:
        normalized = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(normalized) or (normalized <= 0 if positive else normalized < 0):
        adjective = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {adjective}")
    object.__setattr__(record, name, normalized)


def _equipment(record: object, name: str) -> None:
    value = getattr(record, name)
    if value is None:
        return
    if type(value) is not tuple or any(type(item) is not str or not item.strip() for item in value):
        raise TypeError(f"{name} must be a tuple of non-empty strings or None")
    # These are exact inventory identifiers, not names guessed to be interchangeable.
    object.__setattr__(record, name, tuple(sorted({item.strip() for item in value})))


@dataclass(frozen=True)
class ProcessRequirements(Digestible):
    """Supplied whole-step requirements, including workup when explicitly declared.

    ``None`` is unknown.  In particular, ``equipment=()`` declares no equipment;
    ``equipment=None`` leaves it unknown.  All elapsed and active ranges use minutes.
    A periodic check interval is the maximum permitted time between operator checks.

    ``peak_temperature_k``, ``min_pressure_atm`` and ``max_pressure_atm`` declare
    extrema across all operations, including setup and workup.  A reaction-envelope
    temperature is not a substitute for these whole-step extrema.  Unknown extrema
    remain unknown, and callers must still require ``workup_included`` before treating
    the process declaration as covering the entire step.
    """

    elapsed_minutes: Interval | None = None
    active_minutes: Interval | None = None
    attention: Attention | None = None
    check_interval_minutes: float | None = None
    agitation: Agitation | None = None
    equipment: tuple[str, ...] | None = None
    workup_included: bool = False
    provenance: str = ""
    source: SourceCitation | None = None
    peak_temperature_k: float | None = None
    min_pressure_atm: float | None = None
    max_pressure_atm: float | None = None

    def __post_init__(self) -> None:
        # Lazy import keeps this leaf usable by ConditionEnvelope without a module cycle.
        from .conditions import Interval

        for name in ("elapsed_minutes", "active_minutes"):
            value = getattr(self, name)
            if value is not None:
                if type(value) is not Interval:
                    raise TypeError(f"{name} must be an Interval or None")
                if value.unit != "min":
                    raise ValueError(f"{name} must use unit 'min'; convert explicitly")
                if value.lo < 0:
                    raise ValueError(f"{name} must be nonnegative")
        if (self.elapsed_minutes is not None and self.active_minutes is not None
                and self.active_minutes.lo > self.elapsed_minutes.hi):
            raise ValueError("active_minutes cannot require more time than the entire elapsed range")
        if self.attention is not None and type(self.attention) is not Attention:
            raise TypeError("attention must be an Attention or None")
        if self.agitation is not None and type(self.agitation) is not Agitation:
            raise TypeError("agitation must be an Agitation or None")
        _number(self, "check_interval_minutes", positive=True)
        if (self.check_interval_minutes is not None
                and self.attention in (Attention.PASSIVE, Attention.CONTINUOUS)):
            raise ValueError("check_interval_minutes requires periodic attention or an undeclared attention mode")
        for name in ("peak_temperature_k", "min_pressure_atm", "max_pressure_atm"):
            _number(self, name, positive=True)
        if (self.min_pressure_atm is not None and self.max_pressure_atm is not None
                and self.min_pressure_atm > self.max_pressure_atm):
            raise ValueError("min_pressure_atm cannot exceed max_pressure_atm")
        _equipment(self, "equipment")
        if type(self.workup_included) is not bool:
            raise TypeError("workup_included must be a bool")
        if type(self.provenance) is not str:
            raise TypeError("provenance must be a string")
        object.__setattr__(self, "provenance", self.provenance.strip())
        if self.source is not None and type(self.source) is not SourceCitation:
            raise TypeError("source must be a SourceCitation or None")
        if self.is_declared and not self.provenance:
            raise ValueError("declared process requirements must carry non-empty provenance")
        if not self.is_declared and (self.provenance or self.source is not None):
            raise ValueError("process provenance/source must accompany declared requirements")

    @classmethod
    def unknown(cls) -> ProcessRequirements:
        return cls()

    @property
    def is_declared(self) -> bool:
        return self.workup_included or any(
            getattr(self, name) is not None for name in (
                "elapsed_minutes", "active_minutes", "attention", "check_interval_minutes",
                "agitation", "equipment", "peak_temperature_k", "min_pressure_atm", "max_pressure_atm",
            )
        )


_BOUND_NAMES = (
    "max_step_minutes", "max_total_minutes", "max_active_minutes", "allowed_attention",
    "min_check_interval_minutes", "allowed_agitation", "available_equipment",
)


@dataclass(frozen=True)
class ProcessBounds(Digestible):
    """An operator's declared limits; ``None`` leaves that dimension unconstrained.

    Elapsed and active route totals conservatively sum step upper bounds, without
    assuming overlap.  Empty allowed sets deliberately permit no member of that set.
    Equipment identifiers are matched exactly after whitespace normalization.
    """

    schema_version: str = PROCESS_BOUNDS_SCHEMA
    max_step_minutes: float | None = None
    max_total_minutes: float | None = None
    max_active_minutes: float | None = None
    allowed_attention: tuple[Attention, ...] | None = None
    min_check_interval_minutes: float | None = None
    allowed_agitation: tuple[Agitation, ...] | None = None
    available_equipment: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != PROCESS_BOUNDS_SCHEMA:
            raise ValueError(f"schema_version must be exactly {PROCESS_BOUNDS_SCHEMA!r}")
        for name in ("max_step_minutes", "max_total_minutes", "max_active_minutes",
                     "min_check_interval_minutes"):
            _number(self, name)
        for name, enum in (("allowed_attention", Attention), ("allowed_agitation", Agitation)):
            value = getattr(self, name)
            if value is None:
                continue
            if type(value) is not tuple or any(type(item) is not enum for item in value):
                raise TypeError(f"{name} must be a tuple of {enum.__name__} values or None")
            object.__setattr__(self, name, tuple(sorted(set(value), key=lambda item: item.value)))
        _equipment(self, "available_equipment")

    @classmethod
    def of(cls, **bounds: object) -> ProcessBounds:
        return cls(**bounds)

    @classmethod
    def unconstrained(cls) -> ProcessBounds:
        return cls()

    @classmethod
    def quick(cls) -> ProcessBounds:
        """An example preference: up to 60 minutes per step, 120 total, 60 active."""
        return cls(max_step_minutes=60, max_total_minutes=120, max_active_minutes=60,
                   allowed_agitation=(Agitation.NONE, Agitation.MANUAL, Agitation.PERIODIC))

    @classmethod
    def low_touch(cls) -> ProcessBounds:
        """An example preference: periodic/passive attention and checks no more than hourly."""
        return cls(max_step_minutes=10080, max_total_minutes=20160, max_active_minutes=60,
                   allowed_attention=(Attention.PASSIVE, Attention.PERIODIC),
                   min_check_interval_minutes=60,
                   allowed_agitation=(Agitation.NONE, Agitation.PERIODIC))

    @classmethod
    def preset(cls, name: str) -> ProcessBounds:
        if name == "quick":
            return cls.quick()
        if name == "low-touch":
            return cls.low_touch()
        if name in ("unconstrained", "none"):
            return cls.unconstrained()
        raise ValueError("unknown process preset; expected quick, low-touch, or unconstrained")

    @property
    def constrains_anything(self) -> bool:
        return any(getattr(self, name) is not None for name in _BOUND_NAMES)

    def describe(self) -> str:
        parts: list[str] = []
        for name, label in (("max_step_minutes", "step"), ("max_total_minutes", "route"),
                            ("max_active_minutes", "active route")):
            value = getattr(self, name)
            if value is not None:
                parts.append(f"{label}<={value:g} min")
        for name, label in (("allowed_attention", "attention"), ("allowed_agitation", "agitation")):
            value = getattr(self, name)
            if value is not None:
                parts.append(f"{label}=" + ("/".join(item.value.lower() for item in value) or "empty set"))
        if self.min_check_interval_minutes is not None:
            parts.append(f"check interval>={self.min_check_interval_minutes:g} min")
        if self.available_equipment is not None:
            parts.append("equipment=" + ("/".join(self.available_equipment) or "none"))
        return ", ".join(parts) if parts else "unconstrained"


class ProcessFitStatus(str, Enum):
    UNCONSTRAINED = "UNCONSTRAINED"
    FITS = "FITS"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProcessFit(Digestible):
    """A requirements comparison, never a chemical feasibility or safety certificate."""

    status: ProcessFitStatus
    exclusions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.status) is not ProcessFitStatus:
            raise TypeError("status must be a ProcessFitStatus")
        for name in ("exclusions", "gaps"):
            value = getattr(self, name)
            if type(value) is not tuple or any(type(item) is not str or not item.strip() for item in value):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
        if self.status is ProcessFitStatus.EXCLUDED and not self.exclusions:
            raise ValueError("EXCLUDED must have an exclusion")
        if self.status is not ProcessFitStatus.EXCLUDED and self.exclusions:
            raise ValueError("exclusions require EXCLUDED status")
        if self.status is ProcessFitStatus.UNKNOWN and not self.gaps:
            raise ValueError("UNKNOWN must have a gap")
        if self.status in (ProcessFitStatus.FITS, ProcessFitStatus.UNCONSTRAINED) and self.gaps:
            raise ValueError("FITS/UNCONSTRAINED cannot have gaps")


def evaluate_process(envelopes: Iterable[ConditionEnvelope], bounds: ProcessBounds) -> ProcessFit:
    """Compare each declared step and route totals against explicitly selected limits.

    Known violations win over missing information; exclusions and gaps are both retained.
    Even a single unknown step cannot silently disappear from route totals.  A known
    subtotal already over a route limit is enough to exclude despite unknown other steps.
    """
    from .conditions import ConditionEnvelope

    if type(bounds) is not ProcessBounds:
        raise TypeError("bounds must be a ProcessBounds")
    steps = tuple(envelopes)
    if any(type(envelope) is not ConditionEnvelope for envelope in steps):
        raise TypeError("envelopes must contain ConditionEnvelope values")
    if not bounds.constrains_anything:
        return ProcessFit(ProcessFitStatus.UNCONSTRAINED)
    exclusions: list[str] = []
    gaps: list[str] = []
    if not steps:
        return ProcessFit(ProcessFitStatus.UNKNOWN, gaps=("route has no declared process steps",))
    elapsed_upper: list[float] = []
    active_upper: list[float] = []
    for index, envelope in enumerate(steps, start=1):
        requirement = envelope.process if envelope.process is not None else ProcessRequirements.unknown()
        if type(requirement) is not ProcessRequirements:
            raise TypeError("envelope.process must be a ProcessRequirements")
        prefix = f"step {index}"
        if not requirement.workup_included:
            gaps.append(f"{prefix}: whole-step requirements do not explicitly include workup")
        if bounds.max_step_minutes is not None or bounds.max_total_minutes is not None:
            if requirement.elapsed_minutes is None:
                gaps.append(f"{prefix}: elapsed_minutes is undeclared")
            else:
                elapsed_upper.append(requirement.elapsed_minutes.hi)
                if bounds.max_step_minutes is not None and requirement.elapsed_minutes.hi > bounds.max_step_minutes:
                    exclusions.append(f"{prefix}: elapsed upper bound {requirement.elapsed_minutes.hi:g} min "
                                      f"exceeds step limit {bounds.max_step_minutes:g} min")
        if bounds.max_active_minutes is not None:
            if requirement.active_minutes is None:
                gaps.append(f"{prefix}: active_minutes is undeclared")
            else:
                active_upper.append(requirement.active_minutes.hi)
        if bounds.allowed_attention is not None:
            if requirement.attention is None:
                gaps.append(f"{prefix}: attention is undeclared")
            elif requirement.attention not in bounds.allowed_attention:
                exclusions.append(f"{prefix}: attention {requirement.attention.value} is not allowed")
        if bounds.min_check_interval_minutes is not None:
            # An explicitly declared interval remains load-bearing even when the
            # attention mode is missing; a known violation must beat that gap.
            if (requirement.check_interval_minutes is not None
                    and requirement.check_interval_minutes < bounds.min_check_interval_minutes):
                exclusions.append(f"{prefix}: required check interval {requirement.check_interval_minutes:g} min "
                                  f"is shorter than operator minimum {bounds.min_check_interval_minutes:g} min")
            if requirement.attention is None:
                if bounds.allowed_attention is None:
                    gaps.append(f"{prefix}: attention is undeclared for checking the operator check interval")
            elif requirement.attention is Attention.CONTINUOUS:
                if bounds.min_check_interval_minutes > 0:
                    exclusions.append(f"{prefix}: continuous attention conflicts with minimum operator "
                                      f"check interval {bounds.min_check_interval_minutes:g} min")
            elif requirement.attention is Attention.PERIODIC:
                if requirement.check_interval_minutes is None:
                    gaps.append(f"{prefix}: periodic attention check_interval_minutes is undeclared")
        if bounds.allowed_agitation is not None:
            if requirement.agitation is None:
                gaps.append(f"{prefix}: agitation is undeclared")
            elif requirement.agitation not in bounds.allowed_agitation:
                exclusions.append(f"{prefix}: agitation {requirement.agitation.value} is not allowed")
        if bounds.available_equipment is not None:
            if requirement.equipment is None:
                gaps.append(f"{prefix}: equipment is undeclared")
            else:
                missing = sorted(set(requirement.equipment) - set(bounds.available_equipment))
                if missing:
                    exclusions.append(f"{prefix}: required equipment is unavailable: {', '.join(missing)}")

    # fsum can overflow even though each supplied bound is finite; that subtotal
    # unambiguously exceeds every finite limit and must be excluded, never crash.
    def total(values: list[float]) -> float:
        try:
            return math.fsum(values)
        except OverflowError:
            return math.inf

    for values, limit, label in (
        (elapsed_upper, bounds.max_total_minutes, "elapsed"),
        (active_upper, bounds.max_active_minutes, "active"),
    ):
        if limit is not None and total(values) > limit:
            exclusions.append(f"route: known {label} upper-bound sum {total(values):g} min exceeds "
                              f"route limit {limit:g} min")
    status = (ProcessFitStatus.EXCLUDED if exclusions else
              ProcessFitStatus.UNKNOWN if gaps else ProcessFitStatus.FITS)
    return ProcessFit(status, tuple(exclusions), tuple(gaps))
