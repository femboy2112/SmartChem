"""smartchem/capability/assess.py -- the pure verdict fold (FREEZE decision 5).

**LOOK AT ME, I'M THE JUDGE MEESEEKS!** I take a ``CapabilityProfile`` (what a bench HAS) and a
``RouteCapabilityRequirements`` (what a route NEEDS) and, axis by axis, hand back an honest verdict --
never a first-error shortcut, never a silent pass on ignorance. Every axis gets its OWN
:class:`~smartchem.capability.enums.CapabilityStatus` and its OWN full reason tuple; nothing is hidden
behind an earlier failure (decision 5: "retain the FULL per-axis reason set -- never hide multiple
blockers behind a first error").

The fold, exactly as frozen (decision 5), read in THIS order:

1. any axis ``BLOCKED`` -> overall ``BLOCKED`` (a provable hard fact always wins, tier or no tier);
2. else any axis ``UNKNOWN`` -> overall ``UNKNOWN`` (an open question always beats a guessed FIT);
3. else -- every axis is FIT/NOT_APPLICABLE/UNCONSTRAINED -- the **HARD LAW** applies: overall
   ``CAPABILITY_FIT`` additionally requires the route's own readiness ``tier`` to be at least
   ``PROCESS_SPECIFIED``; below that tier the ceiling is ``UNKNOWN``, never ``FIT`` (a route can be
   perfectly resourced and still not have earned the right to claim FIT if nobody ever wrote down a real
   bench procedure for it).

This module never mutates, never searches, never re-derives chemistry -- it is a pure function of its
three inputs, same discipline as ``experiment/readiness.py``'s ``evaluate_route``.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible
from ..data.reagents import Availability
from ..experiment.catalyst_availability import is_obtainable_under
from ..experiment.readiness import PROCESS_SPECIFIED, RouteReadiness, tier_rank
from ..experiment.stock import FitnessVerdict, StockMaterial
from ..process_constraints import ProcessBounds, ProcessFitStatus, evaluate_process_requirements
from .enums import CapabilityStatus, EquipmentCapability
from .profile import CapabilityProfile
from .requirements import MaterialRequirement, RouteCapabilityRequirements

__all__ = ["CAPABILITY_ASSESSMENT_SCHEMA", "AxisResult", "CapabilityAssessment", "assess"]

CAPABILITY_ASSESSMENT_SCHEMA = "smartchem.capability/capability-assessment-v1alpha1"

#: ProcessFitStatus -> CapabilityStatus, a straight 1:1 relabelling (decision 2: DELEGATE to
#: evaluate_process_requirements, never reimplement the comparison it already makes soundly).
_PROCESS_FIT_TO_CAPABILITY: "dict[ProcessFitStatus, CapabilityStatus]" = {
    ProcessFitStatus.UNCONSTRAINED: CapabilityStatus.UNCONSTRAINED,
    ProcessFitStatus.FITS: CapabilityStatus.FIT,
    ProcessFitStatus.EXCLUDED: CapabilityStatus.BLOCKED,
    ProcessFitStatus.UNKNOWN: CapabilityStatus.UNKNOWN,
}


@dataclass(frozen=True)
class AxisResult(Digestible):
    """One axis's verdict + its FULL reason set (never a first-error truncation)."""

    status: CapabilityStatus
    reasons: "tuple[str, ...]"

    def __post_init__(self) -> None:
        if type(self.status) is not CapabilityStatus:
            raise TypeError("status must be a CapabilityStatus")
        if type(self.reasons) is not tuple or any(
            not isinstance(r, str) or not r.strip() for r in self.reasons
        ):
            raise TypeError("reasons must be a tuple of non-empty strings")


@dataclass(frozen=True)
class CapabilityAssessment(Digestible):
    """The full per-axis + overall verdict of one ``RouteCapabilityRequirements`` against one
    ``CapabilityProfile``. Carries the ``profile_digest``/``route_digest`` it was computed under so a
    later transport-layer re-derivation (FREEZE decision 7's ``CAPABILITY-REBIND-ON-LOAD``) can refuse a
    mismatch -- not built here, but this is the record shape that check will re-derive and compare.

    ``CAPABILITY_FIT`` (see :attr:`is_capability_fit`) is NEVER a safety certificate: it means "every
    modeled axis fits", not "this is safe" -- unmodeled hazards stay unmodeled, not cleared.
    """

    schema_version: str
    profile_digest: str
    route_digest: str
    material: AxisResult
    equipment: AxisResult
    physical: AxisResult
    process: AxisResult
    containment: AxisResult
    measurement: AxisResult
    waste: AxisResult
    procurement: AxisResult
    attention_care: AxisResult
    monetary: AxisResult
    overall: CapabilityStatus
    overall_reasons: "tuple[str, ...]"

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_ASSESSMENT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CAPABILITY_ASSESSMENT_SCHEMA!r}")
        for name in ("profile_digest", "route_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        for name in (
            "material", "equipment", "physical", "process", "containment", "measurement",
            "waste", "procurement", "attention_care", "monetary",
        ):
            if type(getattr(self, name)) is not AxisResult:
                raise TypeError(f"{name} must be an AxisResult")
        if type(self.overall) is not CapabilityStatus:
            raise TypeError("overall must be a CapabilityStatus")
        if type(self.overall_reasons) is not tuple or any(
            not isinstance(r, str) or not r.strip() for r in self.overall_reasons
        ):
            raise TypeError("overall_reasons must be a tuple of non-empty strings")

    @property
    def axes(self) -> "tuple[AxisResult, ...]":
        """Every per-axis result, in a fixed order -- the exact tuple :func:`assess` folds over."""
        return (
            self.material, self.equipment, self.physical, self.process, self.containment,
            self.measurement, self.waste, self.procurement, self.attention_care, self.monetary,
        )

    @property
    def is_capability_assessed(self) -> bool:
        """``CAPABILITY_ASSESSED`` (decision 5): trivially true -- an assessment exists iff you're holding
        one. Kept as a named property so a caller never has to re-derive the obvious."""
        return True

    @property
    def is_capability_fit(self) -> bool:
        """``CAPABILITY_FIT`` (decision 5): the overall verdict reached FIT. NOT a safety certificate."""
        return self.overall is CapabilityStatus.FIT


def _membership_axis(
    required: "frozenset", available: "frozenset", *, axis: str, extra_reasons: "tuple[str, ...]" = (),
) -> AxisResult:
    """The shared subset-check shape used by equipment/containment/waste/measurement:
    empty requirement -> NOT_APPLICABLE; every required member present -> FIT; anything missing -> BLOCKED
    (named). Never a fuzzy/partial credit -- a closed-vocabulary subset check, nothing softer. Procurement
    is NOT this shape (:func:`_procurement_axis`, below): it needs a per-catalyst uncertain/None reason
    this generic set-difference has no room for, so it stayed off the shared path on purpose."""
    if not required:
        return AxisResult(
            CapabilityStatus.NOT_APPLICABLE,
            (f"{axis}: no requirement was derived for this route",) + tuple(extra_reasons),
        )
    missing = required - available
    if missing:
        names = ", ".join(sorted(m.value for m in missing))
        return AxisResult(
            CapabilityStatus.BLOCKED,
            (f"{axis}: the declared profile is missing required capability/ies: {names}",) + tuple(extra_reasons),
        )
    names = ", ".join(sorted(m.value for m in required))
    return AxisResult(
        CapabilityStatus.FIT,
        (f"{axis}: the declared profile covers every required capability: {names}",) + tuple(extra_reasons),
    )


def _equipment_axis(
    required: "frozenset[EquipmentCapability]",
    available: "frozenset[EquipmentCapability]",
    unrecognized: "tuple[str, ...]",
) -> AxisResult:
    """The equipment axis's own gate, ahead of the ordinary membership check (FREEZE decision 4): a
    genuinely-untabled sourced apparatus string is an open question about a bench's CAPABILITY, not a
    consumable anyone vetted -- it caps this axis at UNKNOWN before ``_membership_axis`` ever gets to
    compare the recognized set. Vetted consumables never reach here at all (``requirements.py`` drops them
    before this field is built), so this is the honest remainder: apparatus the resolver has never met.
    """
    if unrecognized:
        names = ", ".join(sorted(unrecognized))
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                f"equipment: {len(unrecognized)} sourced apparatus string(s) are untabled in the closed "
                f"resolver and cannot be certified either way against any declared profile: {names}",
            ),
        )
    return _membership_axis(required, available, axis="equipment")


def _procurement_axis(
    catalysts: "tuple[tuple[str, Availability | None], ...]",
    allowed_tiers: "frozenset[Availability]",
) -> AxisResult:
    """Gate #10, profile-relative procurement: does the declared profile's ``allowed_tiers`` actually
    reach every catalyst the route names? No declared catalyst at all -> ``NOT_APPLICABLE`` (silence is
    not a claim). A declared catalyst this projection could not positively classify (``tier is None``)
    BLOCKS unconditionally, no matter how generous the profile -- an open question about a substance never
    gets waved through on a technicality (kills M17: an unrecognized catalyst is not "poor-man-obtainable"
    by default, it is UNCERTIFIABLE). A recognized tier the profile never declared reach for BLOCKS, named
    (kills M18: a research-lab profile that only ever asked for non-industrial tiers does not get an
    industrial catalyst for free just because a lab exists). Weakest link over the declared set -- one
    unobtainable catalyst sinks the whole axis, same discipline as every other membership check here."""
    if not catalysts:
        return AxisResult(
            CapabilityStatus.NOT_APPLICABLE, ("procurement: no catalyst was declared for this route",),
        )
    reasons: "list[str]" = []
    blocked = False
    for name, tier in catalysts:
        if tier is None:
            blocked = True
            reasons.append(
                f"procurement: declared catalyst {name!r} is of uncertain obtainability -- cannot certify "
                "against any declared profile (fail-closed on an unrecognized substance)"
            )
        elif not is_obtainable_under(tier, allowed_tiers):
            blocked = True
            allowed_str = ", ".join(sorted(a.value for a in allowed_tiers)) or "none"
            reasons.append(
                f"procurement: declared catalyst {name!r} is tier {tier.value!r}, not among the declared "
                f"profile's allowed procurement tiers ({allowed_str})"
            )
        else:
            reasons.append(
                f"procurement: declared catalyst {name!r} is tier {tier.value!r}, within the declared "
                "profile's allowed procurement tiers"
            )
    if blocked:
        return AxisResult(CapabilityStatus.BLOCKED, tuple(reasons))
    return AxisResult(CapabilityStatus.FIT, tuple(reasons))


def _material_item_status(
    requirement: MaterialRequirement, inventory: "tuple[StockMaterial, ...]",
) -> "tuple[CapabilityStatus, str]":
    """One :class:`MaterialRequirement` against a declared stock inventory: search every declared stock
    item for the BEST verdict (a real pantry has more than one bottle) -- SATISFIES anywhere -> FIT;
    else UNKNOWN_ASSAY anywhere -> UNKNOWN (a real candidate exists, but needs measuring); else every
    stock item is IDENTITY_ABSENT/INSUFFICIENT_ASSAY -> BLOCKED (nothing in the inventory could EVER meet
    this, a provable negative). An empty inventory, or an UNKNOWN required_assay, never reaches
    ``.satisfies()`` at all -- both are unconditionally UNKNOWN (FREEZE decision 3/5: "UNKNOWN assay never
    FITs"; ``StockMaterial.satisfies`` itself refuses a ``None`` ``min_assay``)."""
    if not inventory:
        return (
            CapabilityStatus.UNKNOWN,
            f"material: no declared stock inventory to check {requirement.role} {requirement.identity!r} "
            f"against ({requirement.evidence_source})",
        )
    if requirement.required_assay is None:
        return (
            CapabilityStatus.UNKNOWN,
            f"material: no declared minimum assay for {requirement.role} {requirement.identity!r} -- "
            "UNKNOWN never rounds up to FIT",
        )
    verdicts = tuple(
        stock.satisfies(requirement.identity, min_assay=requirement.required_assay) for stock in inventory
    )
    if FitnessVerdict.SATISFIES in verdicts:
        return (
            CapabilityStatus.FIT,
            f"material: >=1 declared stock item satisfies {requirement.role} {requirement.identity!r} "
            f"at >= {requirement.required_assay:.4f} assay",
        )
    if FitnessVerdict.UNKNOWN_ASSAY in verdicts:
        return (
            CapabilityStatus.UNKNOWN,
            f"material: a declared stock item's assay interval for {requirement.role} "
            f"{requirement.identity!r} straddles the required {requirement.required_assay:.4f} -- "
            "a measurement is required",
        )
    return (
        CapabilityStatus.BLOCKED,
        f"material: no declared stock item can satisfy {requirement.role} {requirement.identity!r} at "
        f">= {requirement.required_assay:.4f} assay (absent from every bottle, or provably insufficient)",
    )


def _material_axis(
    requirements: "tuple[MaterialRequirement, ...]", inventory: "tuple[StockMaterial, ...]",
) -> AxisResult:
    if not requirements:
        return AxisResult(CapabilityStatus.NOT_APPLICABLE, ("material: no material requirement was derived for this route",))
    statuses: "list[CapabilityStatus]" = []
    reasons: "list[str]" = []
    for requirement in requirements:
        status, reason = _material_item_status(requirement, inventory)
        statuses.append(status)
        reasons.append(reason)
    if CapabilityStatus.BLOCKED in statuses:
        overall = CapabilityStatus.BLOCKED
    elif CapabilityStatus.UNKNOWN in statuses:
        overall = CapabilityStatus.UNKNOWN
    else:
        overall = CapabilityStatus.FIT
    return AxisResult(overall, tuple(reasons))


def _physical_axis(requirement, ceiling) -> AxisResult:
    """``PhysicalBounds`` (route demand) vs ``PhysicalBounds`` (profile ceiling). No existing evaluator
    reuses this exact comparison (unlike ``process``, which delegates to a real function) -- this mirrors
    the same gap/exclude discipline ``process_constraints._evaluate_requirements`` already uses: a known
    excess -> BLOCKED; an undeclared route extremum against a declared ceiling -> UNKNOWN (a floor/ceiling
    can only ever exclude or confirm, never guess); an all-``None`` profile ceiling -> UNCONSTRAINED."""
    if not ceiling.constrains_anything:
        return AxisResult(CapabilityStatus.UNCONSTRAINED, ("physical: the declared profile has no T/P ceiling",))
    reasons: "list[str]" = []
    blocked = False
    unknown = False
    if ceiling.max_temperature_k is not None:
        if requirement.max_temperature_k is None:
            unknown = True
            reasons.append(
                f"physical: route peak temperature is undeclared; cannot certify against the "
                f"{ceiling.max_temperature_k:g} K ceiling"
            )
        elif requirement.max_temperature_k > ceiling.max_temperature_k:
            blocked = True
            reasons.append(
                f"physical: route peak temperature {requirement.max_temperature_k:g} K exceeds the "
                f"{ceiling.max_temperature_k:g} K ceiling"
            )
        else:
            reasons.append(
                f"physical: route peak temperature {requirement.max_temperature_k:g} K is within the "
                f"{ceiling.max_temperature_k:g} K ceiling"
            )
    if ceiling.max_pressure_atm is not None:
        if requirement.max_pressure_atm is None:
            unknown = True
            reasons.append(
                f"physical: route max pressure is undeclared; cannot certify against the "
                f"{ceiling.max_pressure_atm:g} atm ceiling"
            )
        elif requirement.max_pressure_atm > ceiling.max_pressure_atm:
            blocked = True
            reasons.append(
                f"physical: route max pressure {requirement.max_pressure_atm:g} atm exceeds the "
                f"{ceiling.max_pressure_atm:g} atm ceiling"
            )
        else:
            reasons.append(
                f"physical: route max pressure {requirement.max_pressure_atm:g} atm is within the "
                f"{ceiling.max_pressure_atm:g} atm ceiling"
            )
    if ceiling.min_pressure_atm is not None:
        if requirement.min_pressure_atm is None:
            unknown = True
            reasons.append(
                f"physical: route min pressure is undeclared; cannot certify it clears the "
                f"{ceiling.min_pressure_atm:g} atm floor"
            )
        elif requirement.min_pressure_atm < ceiling.min_pressure_atm:
            blocked = True
            reasons.append(
                f"physical: route min pressure {requirement.min_pressure_atm:g} atm is below the "
                f"{ceiling.min_pressure_atm:g} atm floor"
            )
        else:
            reasons.append(
                f"physical: route min pressure {requirement.min_pressure_atm:g} atm clears the "
                f"{ceiling.min_pressure_atm:g} atm floor"
            )
    if blocked:
        return AxisResult(CapabilityStatus.BLOCKED, tuple(reasons))
    if unknown:
        return AxisResult(CapabilityStatus.UNKNOWN, tuple(reasons))
    return AxisResult(CapabilityStatus.FIT, tuple(reasons))


def _process_axis(requirements, bounds: ProcessBounds) -> AxisResult:
    """DELEGATE, never reimplement (decision 2): the real per-step/route-total comparison already lives
    in ``evaluate_process_requirements`` (time/attention/agitation/equipment-string checks); this only
    relabels its verdict onto :class:`CapabilityStatus`."""
    fit = evaluate_process_requirements(requirements, bounds)
    reasons = tuple(f"process: {reason}" for reason in (*fit.exclusions, *fit.gaps))
    if not reasons:
        reasons = (f"process: {fit.status.value}",)
    return AxisResult(_PROCESS_FIT_TO_CAPABILITY[fit.status], reasons)


def _monetary_axis(route_cost, budget) -> AxisResult:
    """A known route cash <= a declared budget ceiling -> FIT; a KNOWN excess (exact cash, or a floor that
    ALREADY exceeds the ceiling) -> BLOCKED; a floor within budget never confirms FIT (M15: the true total
    could still be higher) -> UNKNOWN; mismatched currencies are incomparable, never summed (M16) ->
    UNKNOWN; an unknown route cash against a declared budget -> UNKNOWN, never a fabricated free $0 (M14);
    no declared budget at all -> UNCONSTRAINED."""
    if budget is None or budget.cash is None:
        return AxisResult(CapabilityStatus.UNCONSTRAINED, ("monetary: the declared profile has no budget ceiling",))
    if route_cost.cash is None and route_cost.cash_floor is None:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            ("monetary: route cash is UNKNOWN; cannot certify against the declared budget",),
        )
    if route_cost.currency and budget.currency and route_cost.currency != budget.currency:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                f"monetary: route cash is denominated in {route_cost.currency!r}, budget in "
                f"{budget.currency!r} -- incomparable, never summed across currencies",
            ),
        )
    if route_cost.cash is not None:
        if route_cost.cash <= budget.cash:
            return AxisResult(
                CapabilityStatus.FIT,
                (f"monetary: known route cash {route_cost.cash:g} is within the {budget.cash:g} budget",),
            )
        return AxisResult(
            CapabilityStatus.BLOCKED,
            (f"monetary: known route cash {route_cost.cash:g} exceeds the {budget.cash:g} budget",),
        )
    # cash_floor only: a proven lower bound, never an exact total.
    if route_cost.cash_floor > budget.cash:
        return AxisResult(
            CapabilityStatus.BLOCKED,
            (f"monetary: route cash floor {route_cost.cash_floor:g} already exceeds the {budget.cash:g} budget",),
        )
    return AxisResult(
        CapabilityStatus.UNKNOWN,
        (
            f"monetary: route cash floor {route_cost.cash_floor:g} is within the {budget.cash:g} budget, "
            "but the true total is UNKNOWN -- a floor can only exclude, never confirm a fit",
        ),
    )


def _attention_care_axis(level) -> AxisResult:
    """Informational only (FREEZE decision 2): kept structurally separate from the ``process`` axis's
    operator-declared ``Attention``/``Agitation`` CAPABILITY, so the two attention axes can never silently
    disagree -- there is no profile-side "care capability" field in decision 1's schema to compare this
    hazard-driven DEMAND against, so it never gates the overall fold, but it is retained here, loudly,
    never dropped."""
    return AxisResult(
        CapabilityStatus.NOT_APPLICABLE,
        (
            f"attention_care: the route's hazard-driven care demand is {level.value} (informational; "
            "structurally separate from the process/attention capability axis)",
        ),
    )


def assess(
    profile: CapabilityProfile,
    requirements: RouteCapabilityRequirements,
    route_readiness: RouteReadiness,
) -> CapabilityAssessment:
    """The pure verdict: does ``profile`` satisfy ``requirements``, given ``route_readiness``'s tier?

    Never mutates its inputs, never re-derives chemistry, never re-runs search -- exactly the discipline
    ``experiment.readiness.evaluate_route`` already holds itself to.
    """
    if type(profile) is not CapabilityProfile:
        raise TypeError("profile must be a smartchem.capability.profile.CapabilityProfile")
    if type(requirements) is not RouteCapabilityRequirements:
        raise TypeError("requirements must be a smartchem.capability.requirements.RouteCapabilityRequirements")
    if type(route_readiness) is not RouteReadiness:
        raise TypeError("route_readiness must be a smartchem.experiment.readiness.RouteReadiness")

    material = _material_axis(requirements.material, profile.material_inventory)
    equipment = _equipment_axis(requirements.equipment, profile.equipment, requirements.equipment_unrecognized)
    physical = _physical_axis(requirements.physical, profile.physical_bounds)
    process = _process_axis(requirements.process, profile.process_bounds)
    containment = _membership_axis(requirements.containment, profile.containment, axis="containment")
    measurement = _membership_axis(requirements.measurement, profile.measurement, axis="measurement")
    waste = _membership_axis(
        requirements.waste.categories, profile.waste_handling, axis="waste", extra_reasons=requirements.waste.reasons,
    )
    procurement = _procurement_axis(requirements.procurement_catalysts, profile.procurement)
    attention_care = _attention_care_axis(requirements.attention_care)
    monetary = _monetary_axis(requirements.monetary, profile.budget)

    axes = (
        material, equipment, physical, process, containment, measurement, waste, procurement,
        attention_care, monetary,
    )

    overall_reasons: "list[str]" = []
    if any(axis.status is CapabilityStatus.BLOCKED for axis in axes):
        overall = CapabilityStatus.BLOCKED
        overall_reasons.append("overall: at least one required capability axis is BLOCKED")
    elif any(axis.status is CapabilityStatus.UNKNOWN for axis in axes):
        overall = CapabilityStatus.UNKNOWN
        overall_reasons.append("overall: at least one required capability axis is UNKNOWN")
    else:
        tier = route_readiness.tier
        if tier_rank(tier) < tier_rank(PROCESS_SPECIFIED):
            overall = CapabilityStatus.UNKNOWN
            overall_reasons.append(
                f"overall: every axis fits/is unconstrained, but route readiness tier {tier!r} is below "
                "PROCESS_SPECIFIED -- CAPABILITY_FIT requires PROCESS_SPECIFIED or higher (HARD LAW)"
            )
        else:
            overall = CapabilityStatus.FIT
            overall_reasons.append(
                "overall: every required axis fits and route readiness tier is PROCESS_SPECIFIED or higher"
            )

    return CapabilityAssessment(
        schema_version=CAPABILITY_ASSESSMENT_SCHEMA,
        profile_digest=profile.profile_digest,
        route_digest=requirements.route_digest,
        material=material,
        equipment=equipment,
        physical=physical,
        process=process,
        containment=containment,
        measurement=measurement,
        waste=waste,
        procurement=procurement,
        attention_care=attention_care,
        monetary=monetary,
        overall=overall,
        overall_reasons=tuple(overall_reasons),
    )
