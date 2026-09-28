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

from ..contracts import Digestible, canonical_digest
from ..data.reagents import Availability
from ..experiment.catalyst_availability import is_obtainable_under
from ..experiment.readiness import PROCESS_SPECIFIED, RouteReadiness, tier_rank
from ..experiment.stock import FitnessVerdict, Phase, StockMaterial
from ..process_constraints import ProcessBounds, ProcessFitStatus, evaluate_process_requirements
from .enums import CapabilityStatus, EquipmentCapability, MeasurementMethod
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
    ventilation: AxisResult
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


#: FIT > UNKNOWN > BLOCKED -- the rank used to pick the best composition/phase verdict across bottles and to
#: fold the per-requirement material verdicts (a provable BLOCK beats an open UNKNOWN beats a proven FIT).
_MATERIAL_RANK: "dict[CapabilityStatus, int]" = {
    CapabilityStatus.FIT: 3,
    CapabilityStatus.UNKNOWN: 2,
    CapabilityStatus.BLOCKED: 1,
}


def _species_key_in(requirement: MaterialRequirement, stock: StockMaterial):
    """F44: which key ``requirement`` is ALLOWED to match in THIS bottle. A requirement with a known STRUCTURE
    identity may ONLY be satisfied by a structure-keyed component -- a bare name is weaker evidence and can
    never stand in for a proven structure (the exact downgrade F44 kills; the stock layer already refuses to
    cross the two keys, so this just stops the requirement side trying the name after the structure is absent).
    A requirement with no identity (an ionic/mixture species that cannot resolve to a Molecule) matches by its
    declared NAME. Returns the matched key, or ``None`` if the species is absent under the allowed key."""
    if requirement.identity is not None:
        return requirement.identity if stock.active_fraction_interval(requirement.identity) is not None else None
    if requirement.name is not None:
        return requirement.name if stock.active_fraction_interval(requirement.name) is not None else None
    return None


def _comp_phase_status(
    requirement: MaterialRequirement, stock: StockMaterial,
) -> "tuple[CapabilityStatus, str] | None":
    """The NON-quantity (composition + phase) compatibility of ONE requirement against ONE bottle:
    ``(status, note)`` with status FIT/UNKNOWN/BLOCKED, or ``None`` if the species is absent from this bottle
    under the F44 key. Composition uses the TWO-SIDED band (F43) when the requirement declares one (a wash's
    100%-bicarbonate substitution BLOCKS on the ceiling a one-sided floor would have waved through), else the
    one-sided assay floor, else possession is enough; phase must match a known stock phase (D4). QUANTITY is
    NOT decided here -- it is a finite-pool ALLOCATION (F42), so a single bottle can no longer independently
    witness a whole-route demand."""
    key = _species_key_in(requirement, stock)
    if key is None:
        return None
    statuses: "list[CapabilityStatus]" = []
    notes: "list[str]" = []

    def _add(st: CapabilityStatus, note: str) -> None:
        statuses.append(st)
        notes.append(note)

    if requirement.composition_band is not None:
        lo, hi = requirement.composition_band
        verdict = stock.satisfies_band(key, low=lo, high=hi)
        if verdict is FitnessVerdict.SATISFIES:
            _add(CapabilityStatus.FIT, f"composition within [{lo:.3f}, {hi:.3f}]")
        elif verdict is FitnessVerdict.UNKNOWN_ASSAY:
            _add(CapabilityStatus.UNKNOWN, f"composition straddles [{lo:.3f}, {hi:.3f}] (measure)")
        else:
            _add(CapabilityStatus.BLOCKED, f"composition provably outside [{lo:.3f}, {hi:.3f}]")
    elif requirement.required_assay is not None:
        verdict = stock.satisfies(key, min_assay=requirement.required_assay)
        if verdict is FitnessVerdict.SATISFIES:
            _add(CapabilityStatus.FIT, f"assay >= {requirement.required_assay:.4f}")
        elif verdict is FitnessVerdict.UNKNOWN_ASSAY:
            _add(CapabilityStatus.UNKNOWN, f"assay straddles {requirement.required_assay:.4f} (measure)")
        else:
            _add(CapabilityStatus.BLOCKED, f"assay provably below {requirement.required_assay:.4f}")
    if requirement.phase is not None:
        if stock.phase is Phase.UNKNOWN:
            _add(CapabilityStatus.UNKNOWN, f"stock phase UNKNOWN vs required {requirement.phase.value}")
        elif stock.phase is requirement.phase:
            _add(CapabilityStatus.FIT, f"phase {requirement.phase.value} matches")
        else:
            _add(CapabilityStatus.BLOCKED, f"phase {stock.phase.value} != required {requirement.phase.value}")
    if CapabilityStatus.BLOCKED in statuses:
        status = CapabilityStatus.BLOCKED
    elif CapabilityStatus.UNKNOWN in statuses:
        status = CapabilityStatus.UNKNOWN
    else:
        status = CapabilityStatus.FIT
    return status, f"{stock.material_id}: " + ("; ".join(notes) if notes else "present (possession)")


def _req_species_key(requirement: MaterialRequirement) -> str:
    """A stable species key for grouping requirements in the finite-pool allocation: the canonical structure
    digest for a resolved identity, else the normalized declared name."""
    if requirement.identity is not None:
        try:
            return "s:" + canonical_digest(requirement.identity.canonical())
        except NotImplementedError:
            return "s:" + canonical_digest(requirement.identity)
    return "n:" + (requirement.name or "").strip().casefold()


def _max_flow(n: int, edges: "list[tuple[int, int, float]]", source: int, sink: int) -> float:
    """Minimal Edmonds-Karp max-flow over a tiny graph (a handful of nodes) -- the finite-pool material
    allocation feasibility (F42). Float capacities with an epsilon; these graphs never exceed a dozen nodes."""
    import collections
    cap = [[0.0] * n for _ in range(n)]
    adj: "list[list[int]]" = [[] for _ in range(n)]
    for u, v, c in edges:
        if cap[u][v] == 0.0 and cap[v][u] == 0.0:
            adj[u].append(v)
            adj[v].append(u)
        cap[u][v] += c
    eps = 1e-9
    flow = 0.0
    while True:
        parent = [-1] * n
        parent[source] = source
        queue = collections.deque([source])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if parent[v] == -1 and cap[u][v] > eps:
                    parent[v] = u
                    queue.append(v)
        if parent[sink] == -1:
            break
        push = float("inf")
        v = sink
        while v != source:
            u = parent[v]
            push = min(push, cap[u][v])
            v = u
        v = sink
        while v != source:
            u = parent[v]
            cap[u][v] -= push
            cap[v][u] += push
            v = u
        flow += push
    return flow


def _material_axis(
    requirements: "tuple[MaterialRequirement, ...]", inventory: "tuple[StockMaterial, ...]",
) -> AxisResult:
    """Round IV F42/F43/F44: composition+phase compatibility PER BOTTLE, then a finite-pool quantity
    ALLOCATION where a bottle is spent once (no double-spend). BLOCKED beats UNKNOWN beats FIT over the axis."""
    if not requirements:
        return AxisResult(CapabilityStatus.NOT_APPLICABLE, ("material: no material requirement was derived for this route",))
    if not inventory:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            tuple(f"material: no declared stock inventory to check {r.role} {r.label} ({r.evidence_source})"
                  for r in requirements),
        )
    # -- Phase 1: composition + phase compatibility per requirement (best across bottles) + candidate bottles.
    comp_status: "list[CapabilityStatus]" = []
    comp_note: "list[str]" = []
    candidates: "list[list[int]]" = []   # bottle indices that composition/phase SATISFY (the allocation sources)
    for r in requirements:
        best: "CapabilityStatus | None" = None
        note = ""
        fit_bottles: "list[int]" = []
        for bi, stock in enumerate(inventory):
            outcome = _comp_phase_status(r, stock)
            if outcome is None:
                continue
            st, nt = outcome
            if st is CapabilityStatus.FIT:
                fit_bottles.append(bi)
            if best is None or _MATERIAL_RANK[st] > _MATERIAL_RANK[best]:
                best, note = st, nt
        if best is None:
            gated = (r.composition_band is not None or r.required_assay is not None
                     or r.phase is not None or r.quantity is not None)
            best = CapabilityStatus.BLOCKED if gated else CapabilityStatus.UNKNOWN
            note = ("absent from every declared bottle against a real gate (a provable negative)" if gated
                    else "possession-only (no gate) and absent from every bottle -- an open question")
        comp_status.append(best)
        comp_note.append(note)
        candidates.append(fit_bottles)
    # -- Phase 2: finite-pool quantity allocation (F42). Group composition/phase-FIT requirements that declare a
    # quantity by (species, unit); a bottle is a source for a group iff it composition/phase-satisfies >=1 of the
    # group's requirements. A KNOWN-capacity max-flow that saturates all demands -> FIT; a compatible bottle of
    # unknown/incomparable amount where the known flow falls short -> UNKNOWN; all-known and the flow falls short
    # -> BLOCKED (a provable shortfall: the bottle cannot be spent twice).
    alloc: "dict[int, CapabilityStatus]" = {}
    alloc_note: "dict[int, str]" = {}
    groups: "dict[tuple[str, str], list[int]]" = {}
    for i, r in enumerate(requirements):
        if comp_status[i] is CapabilityStatus.FIT and r.quantity is not None:
            groups.setdefault((_req_species_key(r), r.quantity.unit), []).append(i)
    for (_species, unit), idxs in groups.items():
        total_demand = sum(float(requirements[i].quantity.value) for i in idxs)
        bottle_ids = sorted({bi for i in idxs for bi in candidates[i]})
        known_cap: "dict[int, float]" = {}
        unknown_present = False
        for bi in bottle_ids:
            q = inventory[bi].quantity
            if q is not None and q.unit == unit:
                known_cap[bi] = float(q.value)
            else:
                unknown_present = True   # unknown amount OR a compatible bottle in an incomparable unit
        r_index = {i: pos + 1 for pos, i in enumerate(idxs)}
        b_index = {bi: len(idxs) + 1 + pos for pos, bi in enumerate(known_cap)}
        sink = len(idxs) + 1 + len(known_cap)
        edges: "list[tuple[int, int, float]]" = []
        for i in idxs:
            edges.append((0, r_index[i], float(requirements[i].quantity.value)))
            for bi in candidates[i]:
                if bi in b_index:
                    edges.append((r_index[i], b_index[bi], float("inf")))
        for bi, capf in known_cap.items():
            edges.append((b_index[bi], sink, capf))
        flow = _max_flow(sink + 1, edges, 0, sink) if known_cap else 0.0
        if flow >= total_demand - 1e-9:
            verdict = CapabilityStatus.FIT
            msg = f"finite-pool allocation: {total_demand:g} {unit} demand met from declared stock (no double-spend)"
        elif unknown_present:
            verdict = CapabilityStatus.UNKNOWN
            msg = (f"finite-pool allocation: known stock covers {flow:g} of {total_demand:g} {unit}; a compatible "
                   "bottle of unknown/incomparable amount MAY cover the rest -- UNKNOWN, never assumed")
        else:
            verdict = CapabilityStatus.BLOCKED
            msg = (f"finite-pool allocation: declared stock covers only {flow:g} of {total_demand:g} {unit} "
                   "(a bottle cannot be spent twice) -- a provable shortfall")
        for i in idxs:
            alloc[i] = verdict
            alloc_note[i] = msg
    # -- fold each requirement: composition/phase, refined by the allocation verdict where it entered one.
    statuses: "list[CapabilityStatus]" = []
    reasons: "list[str]" = []
    for i, r in enumerate(requirements):
        st = comp_status[i]
        detail = comp_note[i]
        if i in alloc:
            st = alloc[i]
            detail = f"{comp_note[i]}; {alloc_note[i]}"
        statuses.append(st)
        reasons.append(f"material: {r.role} {r.label} -- {detail}")
    if CapabilityStatus.BLOCKED in statuses:
        overall = CapabilityStatus.BLOCKED
    elif CapabilityStatus.UNKNOWN in statuses:
        overall = CapabilityStatus.UNKNOWN
    else:
        overall = CapabilityStatus.FIT
    return AxisResult(overall, tuple(reasons))


def _physical_axis(requirement, ceiling) -> AxisResult:
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


#: F56/F62 (Decision 11): the COMPLETE set of process-unique dimensions the per-dimension fail-close covers,
#: as a TABLE rather than a hand-scattered checklist -- Wave-C proved a checklist is one forgotten line from a
#: false FIT (attention + agitation were the two originally dropped). Each entry: (label, does the ROUTE
#: declare a real demand on this dimension?, does the BENCH model it with a bound?). A demand on a dimension
#: the bench leaves unmodeled (bound None) caps the process axis at UNKNOWN. Equipment is deliberately EXCLUDED
#: -- the capability EQUIPMENT axis already owns it, so listing it here would double-jeopardy a well-equipped
#: bench whose ProcessBounds happens not to restate its apparatus.
_PROCESS_FAILCLOSE_DIMENSIONS = (
    ("elapsed time",
     lambda r: r.min_elapsed_minutes is not None or r.elapsed_minutes is not None,
     lambda b: b.max_step_minutes is not None or b.max_total_minutes is not None),
    ("active time",
     lambda r: r.min_active_minutes is not None or r.active_minutes is not None,
     lambda b: b.max_active_minutes is not None),
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


def _process_axis(requirements, bounds: ProcessBounds) -> AxisResult:
    """DELEGATE, never reimplement (decision 2): the real per-step/route-total comparison already lives
    in ``evaluate_process_requirements`` (time/attention/agitation/equipment-string checks); this only
    relabels its verdict onto :class:`CapabilityStatus`.

    D6 (kills M29): the delegate returns ``UNCONSTRAINED`` when the BOUNDS declare nothing. If the ROUTE
    nonetheless carries a real declared process requirement, that UNCONSTRAINED is relabelled to UNKNOWN --
    an unbounded bench cannot be certified against a real time/attention/agitation demand. The delegate is
    NOT reimplemented; the relabel guards only the empty-bounds-against-a-real-requirement case."""
    fit = evaluate_process_requirements(requirements, bounds)
    status = _PROCESS_FIT_TO_CAPABILITY[fit.status]
    route_demands = any(r is not None and r.is_declared for r in requirements)
    if status is CapabilityStatus.UNCONSTRAINED and route_demands:
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                "process: the declared profile states NO process bound, but this route carries a real "
                "time/attention/agitation demand -- an unbounded bench cannot be certified against it (D6)",
            ),
        )
    reasons = tuple(f"process: {reason}" for reason in (*fit.exclusions, *fit.gaps))
    if not reasons:
        reasons = (f"process: {fit.status.value}",)
    # F56 (Decision 11): the per-dimension fail-close the PHYSICAL axis got in Wave-C F1, ported here. A real
    # route TIME/check-interval demand on a dimension the bench leaves UNMODELED (its bound is None) cannot be
    # certified -> UNKNOWN, never a silent FIT. The delegate already gaps -> UNKNOWN when a bound IS declared
    # but the route's ceiling is not; this closes the OTHER hole -- a bound left entirely None was silently
    # skipped, so a bench that bounds only attention/agitation waved every unbounded time demand straight to FIT.
    if status is CapabilityStatus.FIT:
        # F56 + F62 (Decision 11): the per-dimension fail-close, driven off the COMPLETE table above so no
        # dimension can silently fall off a hand-written checklist (the F62 root cause -- attention/agitation
        # were dropped). A dimension the ROUTE demands but the BENCH leaves unmodeled (bound None) cannot be
        # certified -> UNKNOWN, never a silent FIT. The delegate already gaps -> UNKNOWN when a bound IS
        # declared but the route's value is not; this closes the other half -- an entirely omitted bound.
        unmodeled = [
            label
            for label, route_demands, bounds_models in _PROCESS_FAILCLOSE_DIMENSIONS
            if any(r is not None and route_demands(r) for r in requirements) and not bounds_models(bounds)
        ]
        if unmodeled:
            return AxisResult(
                CapabilityStatus.UNKNOWN,
                reasons + (
                    f"process: this route declares a real demand on {', '.join(unmodeled)}, but the declared "
                    "profile states NO bound on that dimension -- an unbounded process dimension cannot be "
                    "certified against a real demand (F56/F62/Decision 11, per-dimension)",),
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
    does not clear an ``INFRARED_SPECTROSCOPY`` requirement just because both share a tier."""
    if unrecognized:
        names = ", ".join(sorted(unrecognized))
        return AxisResult(
            CapabilityStatus.UNKNOWN,
            (
                f"measurement: {len(unrecognized)} sourced VERIFY-apparatus string(s) are untabled in the "
                f"closed resolver and cannot be certified either way against any declared profile: {names}",
            ),
        )
    return _membership_axis(required, available, axis="measurement")


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
    physical = _physical_axis(requirements.physical, profile.physical_bounds)
    process = _process_axis(requirements.process, profile.process_bounds)
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
    monetary = _monetary_axis(requirements.monetary, profile.budget)

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
    )
