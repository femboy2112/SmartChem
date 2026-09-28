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
from fractions import Fraction

from ..contracts import Digestible
from ..data.reagents import Availability
from ..experiment.catalyst_availability import is_obtainable_under
from ..experiment.readiness import PROCESS_SPECIFIED, RouteReadiness, tier_rank
from ..experiment.stock import Phase, StockMaterial
from ..material_spec import (
    CERTIFYING_STOCK_EVIDENCE,
    ConcentrationBasis,
    SpecVerdict,
    compare_specification,
    exact_fraction,
)
from ..process_constraints import ProcessFitStatus, evaluate_process_requirements
from .enums import CapabilityStatus, EquipmentCapability, MeasurementMethod
from .profile import CapabilityProfile
from .quantity import QuantityKnowledge, fraction_to_decimal
from .requirements import MaterialRequirement, RouteCapabilityRequirements

__all__ = ["CAPABILITY_ASSESSMENT_SCHEMA", "AxisResult", "CapabilityAssessment", "assess"]

CAPABILITY_ASSESSMENT_SCHEMA = "smartchem.capability/capability-assessment-v1alpha2"

#: ProcessFitStatus -> CapabilityStatus, a straight 1:1 relabelling (decision 2: DELEGATE to
#: evaluate_process_requirements, never reimplement the comparison it already makes soundly).
_PROCESS_FIT_TO_CAPABILITY: "dict[ProcessFitStatus, CapabilityStatus]" = {
    ProcessFitStatus.UNCONSTRAINED: CapabilityStatus.UNCONSTRAINED,
    ProcessFitStatus.FITS: CapabilityStatus.FIT,
    ProcessFitStatus.EXCLUDED: CapabilityStatus.BLOCKED,
    ProcessFitStatus.UNKNOWN: CapabilityStatus.UNKNOWN,
}


def _fold_overall(axes: "tuple[AxisResult, ...]", readiness_tier: str) -> CapabilityStatus:
    """FREEZE decision 5's fold, as a pure function (the one :func:`assess` applies and the one
    :class:`CapabilityAssessment` re-checks on construction): any BLOCKED -> BLOCKED; else any UNKNOWN -> UNKNOWN;
    else FIT iff the readiness tier is at least PROCESS_SPECIFIED (HARD LAW), otherwise UNKNOWN."""
    if any(axis.status is CapabilityStatus.BLOCKED for axis in axes):
        return CapabilityStatus.BLOCKED
    if any(axis.status is CapabilityStatus.UNKNOWN for axis in axes):
        return CapabilityStatus.UNKNOWN
    if tier_rank(readiness_tier) < tier_rank(PROCESS_SPECIFIED):
        return CapabilityStatus.UNKNOWN
    return CapabilityStatus.FIT


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
    ventilation: AxisResult
    measurement: AxisResult
    waste: AxisResult
    procurement: AxisResult
    attention_care: AxisResult
    monetary: AxisResult
    overall: CapabilityStatus
    overall_reasons: "tuple[str, ...]"
    #: D13 P1-4: the readiness tier the HARD LAW was applied under, and the digest of the exact ``RouteReadiness``
    #: record it came from -- so the tier the verdict depends on is part of the verdict's own identity. (NOTE:
    #: ``RouteReadiness`` carries no route digest, so it cannot be cross-checked against ``route_digest`` here.)
    readiness_tier: str
    readiness_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_ASSESSMENT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CAPABILITY_ASSESSMENT_SCHEMA!r}")
        for name in ("profile_digest", "route_digest", "readiness_tier", "readiness_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        for name in (
            "material", "equipment", "physical", "process", "containment", "ventilation",
            "measurement", "waste", "procurement", "attention_care", "monetary",
        ):
            if type(getattr(self, name)) is not AxisResult:
                raise TypeError(f"{name} must be an AxisResult")
        if type(self.overall) is not CapabilityStatus:
            raise TypeError("overall must be a CapabilityStatus")
        if type(self.overall_reasons) is not tuple or any(
            not isinstance(r, str) or not r.strip() for r in self.overall_reasons
        ):
            raise TypeError("overall_reasons must be a tuple of non-empty strings")
        # Wave-C2 (thin-wire forgery): the overall verdict is not free data -- it MUST be the fold of the axes under
        # the HARD LAW and the recorded readiness tier. A record whose ``overall`` says FIT over a BLOCKED axis (or
        # over a sub-PROCESS_SPECIFIED tier) cannot exist, on any wire, however it was built.
        expected = _fold_overall(self.axes, self.readiness_tier)
        if self.overall is not expected:
            raise ValueError(
                f"overall {self.overall.value} is not the fold of its axes under the HARD LAW "
                f"(expected {expected.value}) -- a self-contradictory capability assessment")

    @property
    def axes(self) -> "tuple[AxisResult, ...]":
        """Every per-axis result, in a fixed order -- the exact tuple :func:`assess` folds over."""
        return (
            self.material, self.equipment, self.physical, self.process, self.containment,
            self.ventilation, self.measurement, self.waste, self.procurement, self.attention_care,
            self.monetary,
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
    """The equipment axis's own gate (FREEZE decision 4): a genuinely-untabled sourced apparatus string -- or a
    D13 unread equipment demand (a hardware op naming no apparatus, an applied field) -- is an open question about a
    bench's CAPABILITY and caps this axis at UNKNOWN. Round V: the membership check runs FIRST, so a PROVABLE block
    (a recognized required capability the profile lacks) still wins over the open remainder -- an unread demand can
    never launder a known BLOCKED into UNKNOWN."""
    return _gated_membership_axis(required, available, unrecognized, axis="equipment", what=(
        "sourced equipment demand(s) are untabled in the closed resolver or unread (a hardware op naming no "
        "apparatus, an applied field)"))


def _gated_membership_axis(required, available, unrecognized, *, axis: str, what: str) -> AxisResult:
    base = _membership_axis(required, available, axis=axis)
    if not unrecognized:
        return base
    names = ", ".join(sorted(unrecognized))
    note = (f"{axis}: {len(unrecognized)} {what} and cannot be certified either way against any declared "
            f"profile: {names}",)
    if base.status is CapabilityStatus.BLOCKED:
        return AxisResult(CapabilityStatus.BLOCKED, base.reasons + note)
    return AxisResult(CapabilityStatus.UNKNOWN, note + base.reasons)


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


#: FIT > UNKNOWN > BLOCKED -- the rank used to pick the best per-bottle compatibility verdict for a reason line.
_MATERIAL_RANK: "dict[CapabilityStatus, int]" = {
    CapabilityStatus.FIT: 3,
    CapabilityStatus.UNKNOWN: 2,
    CapabilityStatus.BLOCKED: 1,
}

_SPEC_TO_STATUS: "dict[SpecVerdict, CapabilityStatus]" = {
    SpecVerdict.SATISFIES: CapabilityStatus.FIT,
    SpecVerdict.VIOLATES: CapabilityStatus.BLOCKED,
    SpecVerdict.UNDETERMINED: CapabilityStatus.UNKNOWN,
}


def _species_key_in(requirement: MaterialRequirement, stock: StockMaterial):
    """F44: which key ``requirement`` is ALLOWED to match in THIS bottle. A requirement with a known STRUCTURE
    identity may ONLY be satisfied by a structure-keyed component -- a bare name is weaker evidence and can never
    stand in for a proven structure. A requirement with no identity matches by its declared NAME. Returns the matched
    key, or ``None`` if the species is absent under the allowed key."""
    if requirement.identity is not None:
        return requirement.identity if stock.active_fraction_interval(requirement.identity) is not None else None
    if requirement.name is not None:
        return requirement.name if stock.active_fraction_interval(requirement.name) is not None else None
    return None


def _fold_status(statuses: "list[CapabilityStatus]") -> CapabilityStatus:
    if CapabilityStatus.BLOCKED in statuses:
        return CapabilityStatus.BLOCKED
    if CapabilityStatus.UNKNOWN in statuses:
        return CapabilityStatus.UNKNOWN
    return CapabilityStatus.FIT


@dataclass(frozen=True)
class _Edge:
    """Phase-1 compatibility of ONE requirement with ONE bottle (the species is present under the F44 key)."""

    status: CapabilityStatus
    commensurable: bool   # a G- source: drawing X of this bottle provably supplies X of THIS requirement
    note: str


def _edge(requirement: MaterialRequirement, stock: StockMaterial) -> "_Edge | None":
    """D2 Phase 1 for one (requirement, bottle): the specification verdict from THE comparison law
    (:func:`smartchem.material_spec.compare_specification` over ``stock.spec_view``) folded with phase (unknown stock
    phase -> UNKNOWN; mismatch -> BLOCKED). ``None`` if the species is absent from the bottle.

    D13 commensurability (the G- rule): the bottle's draw counts toward this requirement's demand only if the
    requirement's specification is NON-EMPTY (composition/states) and SATISFIED -- the bottle IS the specified
    material -- or the matched species is PROVABLY pure (fraction basis, certifying evidence, exact lower bound 1 -- Wave-C K2).
    Otherwise a bottle is only a G+ (possible) source: 25 mL of a 5% solution is not 25 mL of the solute."""
    key = _species_key_in(requirement, stock)
    if key is None:
        return None
    view = stock.spec_view(key)
    spec_verdict, spec_notes = compare_specification(requirement.specification, view)
    statuses = [_SPEC_TO_STATUS[spec_verdict]]
    notes = [f"specification {spec_verdict.value}" + (f" ({'; '.join(spec_notes)})" if spec_notes else "")]
    if requirement.phase is not None:
        if stock.phase is Phase.UNKNOWN:
            statuses.append(CapabilityStatus.UNKNOWN)
            notes.append(f"stock phase UNKNOWN vs required {requirement.phase.value}")
        elif stock.phase is requirement.phase:
            statuses.append(CapabilityStatus.FIT)
            notes.append(f"phase {requirement.phase.value} matches")
        else:
            statuses.append(CapabilityStatus.BLOCKED)
            notes.append(f"phase {stock.phase.value} != required {requirement.phase.value}")
    status = _fold_status(statuses)
    spec = requirement.specification
    spec_nonempty = spec.composition is not None or bool(spec.states)
    # Wave-C K2: "provably the pure species" needs a FRACTION basis (1 mol/L is a concentration, not purity), CERTIFYING
    # stock evidence (a bare 1.0 or an ASSUMED [1, 1] certifies nothing -- D6/D8), and an exact lower bound of 1
    # read from the evidence record itself (spec_view uses the record's exact decimals, never the float slot).
    pure = (view is not None
            and view.basis in (ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION)
            and view.interval_evidence in CERTIFYING_STOCK_EVIDENCE
            and view.interval[0] == 1)
    commensurable = status is CapabilityStatus.FIT and (
        (spec_nonempty and spec_verdict is SpecVerdict.SATISFIES) or pure)
    if status is CapabilityStatus.FIT and not commensurable:
        notes.append("not a proven draw of this material (empty specification and species not provably pure) -- "
                     "a possible source only")
    return _Edge(status, commensurable, f"{stock.material_id}: {status.value}: " + "; ".join(notes))


def _stock_amount(stock: StockMaterial) -> "tuple[str, Fraction] | None":
    """A bottle's declared quantity as ``(unit, exact Fraction)``, or ``None`` if undeclared or not an exact decimal
    under the strict grammar (an unparseable amount is UNKNOWN capacity, never a float guess)."""
    if stock.quantity is None:
        return None
    try:
        return stock.quantity.unit.strip(), exact_fraction(stock.quantity.value, "stock quantity")
    except (ValueError, TypeError, AttributeError):
        return None


def _max_flow(edges: "list[tuple[object, object, Fraction]]", source: object, sink: object) -> Fraction:
    """Edmonds-Karp over EXACT :class:`~fractions.Fraction` capacities -- no epsilon, no float. Terminates in
    O(V E^2) augmentations independent of the capacity values (shortest augmenting paths)."""
    import collections

    cap: "dict[tuple[object, object], Fraction]" = collections.defaultdict(Fraction)
    adj: "dict[object, list[object]]" = collections.defaultdict(list)
    for u, v, c in edges:
        if (u, v) not in cap and (v, u) not in cap:
            adj[u].append(v)
            adj[v].append(u)
        cap[(u, v)] += c
        cap[(v, u)] += 0
    flow = Fraction(0)
    while True:
        parent: "dict[object, object]" = {source: source}
        queue = collections.deque([source])
        while queue and sink not in parent:
            u = queue.popleft()
            for v in adj[u]:
                if v not in parent and cap[(u, v)] > 0:
                    parent[v] = u
                    queue.append(v)
        if sink not in parent:
            return flow
        path = []
        v = sink
        while v != source:
            path.append((parent[v], v))
            v = parent[v]
        push = min(cap[e] for e in path)
        for u, v in path:
            cap[(u, v)] -= push
            cap[(v, u)] += push
        flow += push


def _dec(value: Fraction) -> str:
    try:
        return fraction_to_decimal(value)
    except ValueError:
        return str(value)


def _material_axis(
    requirements: "tuple[MaterialRequirement, ...]", inventory: "tuple[StockMaterial, ...]",
) -> AxisResult:
    """Round V D2 -- the GLOBAL package-allocation theorem.

    Phase 1: per (requirement, bottle) compatibility (:func:`_edge`).
    Phase 2: ONE exact flow network per unit domain ``u`` across ALL requirements; each bottle is ONE node with ONE
    capacity edge. G- (pessimistic): edges only from FIT + commensurable bottles, capacity = the bottle's exact
    quantity in ``u`` else 0. G+ (optimistic): edges from FIT or UNKNOWN bottles, capacity = exact quantity in ``u``
    else the domain's total demand (a finite stand-in for "unknown").

    BLOCKED iff some domain has F+ < T, or a positive-demand requirement has NO G+ edge (a typed species provably
    absent from, or incompatible with, every declared bottle; an untyped raw-text requirement with no edge is UNKNOWN
    -- absence under a raw string proves nothing). FIT iff every requirement's quantity is EXACT and F- == T in every
    domain. Else UNKNOWN. A bottle's known capacity sits in exactly one domain, so no FIT spends a package twice."""
    if not requirements:
        return AxisResult(CapabilityStatus.NOT_APPLICABLE, ("material: no material requirement was derived for this route",))
    if not inventory:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            tuple(f"material: no declared stock inventory to check {r.role} {r.label} (quantity "
                  f"{r.quantity.render()}; {r.evidence_source})" for r in requirements),
        )
    # -- Phase 1 ------------------------------------------------------------------------------------------------
    edges: "dict[tuple[int, int], _Edge]" = {}
    for ri, r in enumerate(requirements):
        for bi, stock in enumerate(inventory):
            e = _edge(r, stock)
            if e is not None:
                edges[(ri, bi)] = e
    amounts = [_stock_amount(stock) for stock in inventory]
    blocked = False
    unknown = False
    reasons: "list[str]" = []
    for ri, r in enumerate(requirements):
        mine = [edges[(ri, bi)] for bi in range(len(inventory)) if (ri, bi) in edges]
        possible = [e for e in mine if e.status is not CapabilityStatus.BLOCKED]
        knowledge = r.quantity.knowledge
        if knowledge is not QuantityKnowledge.EXACT:
            unknown = True
        if not possible:
            if r.untyped_source_text:
                unknown = True
                verdict = ("no bottle is keyed by this raw source text -- absence under an untyped name proves "
                           "nothing: UNKNOWN")
            else:
                blocked = True
                verdict = ("absent from, or provably incompatible with, every declared bottle against a positive "
                           "demand: BLOCKED")
        elif not any(e.commensurable for e in possible):
            unknown = True
            verdict = "only POSSIBLE sources (no proven, commensurable draw): at best UNKNOWN"
        else:
            verdict = "has a proven, commensurable source"
        detail = " | ".join(e.note for e in mine) if mine else "no declared bottle carries this species"
        reasons.append(f"material: {r.role} {r.label} -- quantity {r.quantity.render()}; {verdict}; bottles: {detail}")
    # -- Phase 2: one allocation per unit domain ----------------------------------------------------------------
    demands = [r.quantity.exact_by_unit() for r in requirements]
    domains = sorted({u for d in demands for u in d})
    for u in domains:
        total = sum((d[u] for d in demands if u in d), Fraction(0))
        pess: "list[tuple[object, object, Fraction]]" = []
        opt: "list[tuple[object, object, Fraction]]" = []
        for ri, d in enumerate(demands):
            if u not in d:
                continue
            pess.append(("S", ("r", ri), d[u]))
            opt.append(("S", ("r", ri), d[u]))
            for bi in range(len(inventory)):
                e = edges.get((ri, bi))
                if e is None or e.status is CapabilityStatus.BLOCKED:
                    continue
                opt.append((("r", ri), ("b", bi), total))
                if e.commensurable:
                    pess.append((("r", ri), ("b", bi), total))
        for bi, amount in enumerate(amounts):
            if amount is not None and amount[0] == u:
                pess.append((("b", bi), "T", amount[1]))
                opt.append((("b", bi), "T", amount[1]))
            else:
                opt.append((("b", bi), "T", total))
        f_pess = _max_flow(pess, "S", "T")
        f_opt = _max_flow(opt, "S", "T")
        if f_opt < total:
            blocked = True
            verdict = "BLOCKED (even the optimistic allocation falls short -- a bottle cannot be spent twice)"
        elif f_pess < total:
            unknown = True
            verdict = "UNKNOWN (only an allocation through unproven/unknown-amount sources could cover it)"
        else:
            verdict = "FIT (proven allocation, each bottle spent once)"
        reasons.append(f"material allocation [{u}]: total demand {_dec(total)} {u}; proven (G-) {_dec(f_pess)} {u}; "
                       f"optimistic (G+) {_dec(f_opt)} {u} -> {verdict}")
    status = (CapabilityStatus.BLOCKED if blocked else CapabilityStatus.UNKNOWN if unknown else CapabilityStatus.FIT)
    reasons.append(f"material allocation verdict: {status.value} (FIT requires every quantity EXACT and a proven "
                   "allocation in every unit domain)")
    return AxisResult(status, tuple(reasons))


def _physical_axis(requirement, ceiling, *, unresolved: "tuple[str, ...]" = ()) -> AxisResult:
    """D13 wrapper: a stated T/P demand the projection could not read into typed bounds (``unresolved``) caps the
    physical axis at UNKNOWN (a provable BLOCK still wins) -- never an UNCONSTRAINED/FIT pass over an unread demand."""
    result = _physical_axis_bounds(requirement, ceiling)
    if not unresolved:
        return result
    notes = tuple(f"physical: {u}" for u in unresolved)
    if result.status is CapabilityStatus.BLOCKED:
        return AxisResult(CapabilityStatus.BLOCKED, result.reasons + notes)
    return AxisResult(CapabilityStatus.UNKNOWN, result.reasons + notes + (
        "physical: a stated temperature/pressure demand could not be read into the typed bounds -- UNKNOWN (D13)",))


def _physical_axis_bounds(requirement, ceiling) -> AxisResult:
    """``PhysicalBounds`` (route demand) vs ``PhysicalBounds`` (profile ceiling). Mirrors the gap/exclude
    discipline ``process_constraints`` uses: a known excess -> BLOCKED; an undeclared route extremum against
    a declared ceiling -> UNKNOWN.

    D6 (kills M29): an all-``None`` profile ceiling no longer rides straight to FIT. If the ROUTE declares a
    real T/P extremum against a bench that declared no bound -> UNKNOWN ("the bench declared no bound against
    a real demand"), NEVER a fabricated UNCONSTRAINED pass. UNCONSTRAINED is retained ONLY for the genuinely-
    outside-the-question case: no route requirement AND no profile bound."""
    if not ceiling.constrains_anything:
        if requirement.constrains_anything:
            demand = ", ".join(
                f"{label}={value:g}"
                for label, value in (
                    ("T_max_K", requirement.max_temperature_k),
                    ("P_min_atm", requirement.min_pressure_atm),
                    ("P_max_atm", requirement.max_pressure_atm),
                )
                if value is not None
            )
            return AxisResult(
                CapabilityStatus.UNKNOWN,
                (
                    "physical: the declared profile states NO T/P ceiling, but this route carries a real "
                    f"demand ({demand}) -- an unbounded bench cannot be certified against a real extremum (D6)",
                ),
            )
        return AxisResult(
            CapabilityStatus.UNCONSTRAINED,
            ("physical: no route T/P requirement and no profile ceiling -- outside the question",),
        )
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
    # Wave-C F1 (kills the per-DIMENSION hole evil-morty + dalembert both proved): the per-field block
    # above iterates the CEILING's declared dimensions, so a route demand on a dimension the ceiling leaves
    # ``None`` was never read -- a temp-only bench rode to FIT against a real, unbounded PRESSURE demand it
    # never claimed. D6's all-``None`` guard fired only when the ceiling constrained NOTHING; apply the SAME
    # rule PER DIMENSION here: a real route demand on a dimension whose profile ceiling is ``None`` is an
    # unbounded dimension that cannot be certified against a real extremum -> UNKNOWN (fail-closed), never a
    # silent FIT. Restores the monotonicity dalembert's incision violated (adding an unrelated bound must
    # never launder an unmet demand from UNKNOWN to FIT).
    for _dim, _demand, _ceil in (
        ("peak temperature (K)", requirement.max_temperature_k, ceiling.max_temperature_k),
        ("max pressure (atm)", requirement.max_pressure_atm, ceiling.max_pressure_atm),
        ("min pressure (atm)", requirement.min_pressure_atm, ceiling.min_pressure_atm),
    ):
        if _demand is not None and _ceil is None:
            unknown = True
            reasons.append(
                f"physical: route {_dim} {_demand:g} is a real demand but the declared profile states NO "
                "bound on that dimension -- an unbounded dimension cannot be certified against a real "
                "extremum (D6, per-dimension)"
            )
    if blocked:
        return AxisResult(CapabilityStatus.BLOCKED, tuple(reasons))
    if unknown:
        return AxisResult(CapabilityStatus.UNKNOWN, tuple(reasons))
    return AxisResult(CapabilityStatus.FIT, tuple(reasons))


#: F56/F62 (Decision 11) + Round V D10: the COMPLETE set of process-unique dimensions the per-dimension fail-close
#: covers, as a TABLE. Each entry: (label, does the ROUTE declare a real demand on it?, how the BENCH side is read).
#: TIME dimensions are read through the D10 declaration state (``process_dimension_state(profile, field)`` ->
#: UNDECLARED / DECLARED_BOUND / NO_LIMIT); attention/agitation/check-interval keep their bound test (they may never
#: be NO_LIMIT). A demand on an UNDECLARED / unmodeled dimension caps the process axis at UNKNOWN. Equipment is
#: deliberately EXCLUDED -- the capability EQUIPMENT axis owns it.
def _ELAPSED_DEMAND(r) -> bool:  # noqa: N802 -- a table entry, named like the constants beside it
    return r.min_elapsed_minutes is not None or r.elapsed_minutes is not None


def _ACTIVE_DEMAND(r) -> bool:  # noqa: N802
    return r.min_active_minutes is not None or r.active_minutes is not None


_PROCESS_TIME_DIMENSIONS = (
    ("step elapsed time", _ELAPSED_DEMAND, "max_step_minutes"),
    ("route-total elapsed time", _ELAPSED_DEMAND, "max_total_minutes"),
    ("active time", _ACTIVE_DEMAND, "max_active_minutes"),
)
_PROCESS_FAILCLOSE_DIMENSIONS = (
    ("operator check interval",
     lambda r: r.check_interval_minutes is not None,
     lambda b: b.min_check_interval_minutes is not None),
    ("attention mode",
     lambda r: r.attention is not None,
     lambda b: b.allowed_attention is not None),
    ("agitation mode",
     lambda r: r.agitation is not None,
     lambda b: b.allowed_agitation is not None),
)


def _process_dimension_gaps(requirements, profile: CapabilityProfile) -> "tuple[list[str], list[str]]":
    """Per-dimension declaration check (D10): returns ``(unmodeled, no_limit)`` labels over the dimensions the ROUTE
    actually demands. UNDECLARED time dimension / unbounded non-time dimension -> ``unmodeled``; an operator NO_LIMIT
    preference -> ``no_limit`` (not a gap, but tagged: a preference, not a measured capability)."""
    from .declarations import DimensionDeclaration, process_dimension_state  # D10 (waste-process owner)

    bounds = profile.process_bounds
    demanded = [r for r in requirements if r is not None]
    unmodeled: "list[str]" = []
    no_limit: "list[str]" = []
    for label, route_demands, field_name in _PROCESS_TIME_DIMENSIONS:
        if not any(route_demands(r) for r in demanded):
            continue
        state = process_dimension_state(profile, field_name)
        if state is DimensionDeclaration.UNDECLARED:
            unmodeled.append(label)
        elif state is DimensionDeclaration.NO_LIMIT:
            no_limit.append(label)
    for label, route_demands, bounds_models in _PROCESS_FAILCLOSE_DIMENSIONS:
        if any(route_demands(r) for r in demanded) and not bounds_models(bounds):
            unmodeled.append(label)
    return unmodeled, no_limit


def _process_axis(requirements, profile: CapabilityProfile, *, unresolved: "tuple[str, ...]" = ()) -> AxisResult:
    """DELEGATE, never reimplement (decision 2): the per-step/route-total comparison lives in
    ``evaluate_process_requirements``; this relabels its verdict onto :class:`CapabilityStatus` and then applies the
    D10 per-dimension declaration law, which needs the PROFILE (its ``no_limit_dimensions``), not just the bounds:

    * UNDECLARED dimension + a real route demand -> UNKNOWN (an unbounded bench cannot be certified against it);
    * DECLARED_BOUND -> the delegate compares;
    * NO_LIMIT (time dimensions only) + demand -> not a gap; the reason is tagged "operator NO_LIMIT preference, not
      measured capability".

    When the delegate returns UNCONSTRAINED (no ProcessBounds field set at all) and the route declares a process
    demand, the axis is FIT only if every demanded dimension is NO_LIMIT and every step carries a process record;
    otherwise UNKNOWN (D6). ``unresolved`` (D13: a duration stated outside the process record's elapsed ceiling)
    caps the axis at UNKNOWN; a provable EXCLUDED still wins."""
    bounds = profile.process_bounds
    fit = evaluate_process_requirements(requirements, bounds)
    status = _PROCESS_FIT_TO_CAPABILITY[fit.status]
    route_demands = any(r is not None and r.is_declared for r in requirements)
    unmodeled, no_limit = _process_dimension_gaps(requirements, profile)
    reasons = tuple(f"process: {reason}" for reason in (*fit.exclusions, *fit.gaps))
    if not reasons:
        reasons = (f"process: {fit.status.value}",)
    reasons += tuple(f"process: {label} -- operator NO_LIMIT preference, not measured capability"
                     for label in no_limit)
    reasons += tuple(f"process: {u}" for u in unresolved)
    if status is CapabilityStatus.UNCONSTRAINED and route_demands:
        undeclared_steps = [i for i, r in enumerate(requirements, start=1) if r is None]
        if unmodeled or undeclared_steps or not no_limit:
            detail = []
            if unmodeled:
                detail.append(f"no bound declared on {', '.join(unmodeled)}")
            if undeclared_steps:
                detail.append(f"step(s) {', '.join(map(str, undeclared_steps))} carry no process record")
            return AxisResult(
                CapabilityStatus.UNKNOWN,
                reasons + (
                    "process: the declared profile states NO process bound, but this route carries a real "
                    "time/attention/agitation demand -- an unbounded bench cannot be certified against it (D6"
                    + (f"; {'; '.join(detail)}" if detail else "") + ")",),
            )
        status = CapabilityStatus.FIT
    if status is CapabilityStatus.BLOCKED:
        return AxisResult(status, reasons)
    if status is CapabilityStatus.FIT and unmodeled:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            reasons + (
                f"process: this route declares a real demand on {', '.join(unmodeled)}, but the declared profile "
                "leaves that dimension UNDECLARED -- an unbounded process dimension cannot be certified against a "
                "real demand (F56/F62/D10, per-dimension)",),
        )
    if unresolved and status in (CapabilityStatus.FIT, CapabilityStatus.UNCONSTRAINED):
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            reasons + ("process: a stated duration is not covered by the process record -- UNKNOWN (D13)",),
        )
    return AxisResult(status, reasons)


def _measurement_axis(
    required: "frozenset[MeasurementMethod]",
    available: "frozenset[MeasurementMethod]",
    unrecognized: "tuple[str, ...]",
) -> AxisResult:
    """The measurement axis's own gate (D5, mirrors ``_equipment_axis``): a genuinely-untabled VERIFY
    apparatus string is an open question about a bench's analytical CAPABILITY -> caps the axis at UNKNOWN
    before the ordinary membership check. Otherwise the comparison is on the SPECIFIC
    :class:`MeasurementMethod` member (NEVER the coarse tier, kills M28): a bench with an NMR but not an IR
    does not clear an ``INFRARED_SPECTROSCOPY`` requirement just because both share a tier. Round V: a provable
    BLOCK from the membership check wins over the unrecognized remainder."""
    return _gated_membership_axis(required, available, unrecognized, axis="measurement", what=(
        "sourced measurement demand(s) are untabled in the closed resolver or unread (a stated analytical "
        "verification with no VERIFY apparatus)"))


def _ventilation_axis() -> AxisResult:
    """D8: an EXPLICIT reserved axis, surfaced -- never a silent green check (kills M32), never dropped. No
    sourced evidence in this corpus forces a ventilation requirement distinct from containment/off-gas, so
    0.9 derives none; the reserved label makes the scope explicit. M6 stays hard elsewhere: OUTDOOR /
    ventilation NEVER substitutes for a declared containment requirement (the containment axis reads
    ``profile.containment`` only)."""
    return AxisResult(
        CapabilityStatus.NOT_APPLICABLE,
        (
            "ventilation: RESERVED -- declared but not assessed in 0.9; no sourced ventilation requirement; "
            "OUTDOOR never substitutes for containment",
        ),
    )


def _monetary_axis(route_cost, budget, *, no_limit: bool = False) -> AxisResult:
    """A known route cash <= a declared budget ceiling -> FIT; a KNOWN excess (exact cash, or a floor that
    ALREADY exceeds the ceiling) -> BLOCKED; a floor within budget never confirms FIT (M15: the true total
    could still be higher) -> UNKNOWN; mismatched currencies are incomparable, never summed (M16) ->
    UNKNOWN; an unknown route cash against a declared budget -> UNKNOWN, never a fabricated free $0 (M14).

    D13 (Round V): NO declared budget is UNDECLARED, not "unconstrained" -- every route consumes purchased
    materials, so an undeclared budget against that real demand is UNKNOWN. Only an explicit operator NO_LIMIT
    preference on ``budget`` (``profile.no_limit_dimensions``) passes it, tagged as a preference."""
    if budget is None or budget.cash is None:
        if no_limit:
            return AxisResult(
                CapabilityStatus.FIT,
                ("monetary: budget -- operator NO_LIMIT preference, not measured capability",),
            )
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            ("monetary: the declared profile states NO budget (UNDECLARED), but every route consumes purchased "
             "materials -- an undeclared budget cannot be certified against that demand (D13)",),
        )
    if route_cost.cash is None and route_cost.cash_floor is None:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            ("monetary: route cash is UNKNOWN; cannot certify against the declared budget",),
        )
    # D7 (kills M30/M31) + Wave-C F2 (an empty denominator is NOT a wildcard): to compare cash at ALL,
    # BOTH sides must declare a currency AND a unit, and each pair must MATCH -- the same (currency, unit)
    # law ``affordability.dominates`` holds. A missing/empty denominator on either side is an UNESTABLISHED
    # basis, not a free match -> UNKNOWN (fail-closed), never a raw-number compare (the old ``if x and y and
    # x!=y`` guard skipped on an empty string and fell through to the raw compare). A $/metric-ton or
    # $/mol-product cost vs a total-$ budget is likewise a denomination mismatch -> UNKNOWN. 0.9 builds no
    # production-quantity bridge (no currency/quantity engine).
    if not (route_cost.currency and budget.currency) or route_cost.currency != budget.currency:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                f"monetary: route cash currency {route_cost.currency!r} vs budget {budget.currency!r} -- "
                "an undeclared or mismatched currency is incomparable, never summed (fail-closed)",
            ),
        )
    if not (route_cost.unit and budget.unit) or route_cost.unit != budget.unit:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                f"monetary: route cash denominated per {route_cost.unit!r}, budget per {budget.unit!r} -- "
                "an undeclared or mismatched denomination is incomparable, never compared by raw number "
                "(no production-quantity bridge)",
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
    physical = _physical_axis(requirements.physical, profile.physical_bounds,
                              unresolved=requirements.physical_unresolved)
    process = _process_axis(requirements.process, profile, unresolved=requirements.process_unresolved)
    # D9: surface the resolved procedure-hazard containment contributions AND the unresolved-hazard notes on
    # the containment axis -- the fold is observable, never silent. M6 stays hard: this reads
    # ``profile.containment`` only; ventilation never clears it.
    containment = _membership_axis(
        requirements.containment, profile.containment, axis="containment",
        extra_reasons=requirements.containment_reasons + requirements.hazard_unresolved,
    )
    if requirements.hazard_unresolved and containment.status in (
        CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE,
    ):
        # F47: a required procedure material whose hazard status is UNRESOLVED means the containment capability
        # it needs cannot be determined -> UNKNOWN, never a pass. A safety disclaimer cannot turn an unassessed
        # capability NEED into FIT: the capability question is "what containment does this route REQUIRE?", not
        # "is it safe?". A provable BLOCK (a known containment requirement unmet) still wins over this.
        containment = AxisResult(
            CapabilityStatus.UNKNOWN,
            containment.reasons + (
                "containment: one or more required procedure materials carry an UNRESOLVED hazard status, so the "
                "containment capability they require cannot be determined -- UNKNOWN, not a pass (F47)",),
        )
    ventilation = _ventilation_axis()
    measurement = _measurement_axis(
        requirements.measurement, profile.measurement, requirements.measurement_unrecognized,
    )
    waste = _membership_axis(
        requirements.waste.categories, profile.waste_handling, axis="waste",
        extra_reasons=requirements.waste.reasons + requirements.waste.unresolved,
    )
    if requirements.waste.unresolved and waste.status in (
        CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE,
    ):
        # F48/F49: a required waste stream whose disposal routing is UNRESOLVED means the waste capability the
        # route needs cannot be determined -> UNKNOWN, never a pass. Unknown waste is not benign waste.
        waste = AxisResult(
            CapabilityStatus.UNKNOWN,
            waste.reasons + (
                "waste: one or more required waste streams have UNRESOLVED disposal routing, so the waste "
                "capability this route requires cannot be determined -- UNKNOWN, not a pass (F48/F49)",),
        )
    procurement = _procurement_axis(requirements.procurement_catalysts, profile.procurement)
    attention_care = _attention_care_axis(requirements.attention_care)
    monetary = _monetary_axis(
        requirements.monetary, profile.budget,
        no_limit="budget" in getattr(profile, "no_limit_dimensions", frozenset()),
    )

    axes = (
        material, equipment, physical, process, containment, ventilation, measurement, waste,
        procurement, attention_care, monetary,
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
        ventilation=ventilation,
        measurement=measurement,
        waste=waste,
        procurement=procurement,
        attention_care=attention_care,
        monetary=monetary,
        overall=overall,
        overall_reasons=tuple(overall_reasons),
        readiness_tier=route_readiness.tier,
        readiness_digest=route_readiness.digest,
    )
