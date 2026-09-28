"""smartchem/capability/requirements.py -- the PURE requirement projection (Round III D1-D9, Round V D1/D3/D9/D13).

**Look at me, I'm a Meeseeks who only ever ASKS questions!** ``compile_capability_requirements`` reads ONE
``ExperimentRoute`` and answers, axis by axis, "what does the sourced evidence say THIS route needs?" -- and it is
FORBIDDEN from ever peeking at a ``CapabilityProfile`` to answer that question. A requirement compiled here has no
idea whether anyone's bench can meet it; that verdict is :mod:`smartchem.capability.assess`'s job.

Round V burned down the last lie of convenience on the material side: a global adjective table that "knew" what a
formulation word meant. The compiler now contains NO formulation vocabulary and NO reagent or target identity:

* **Material semantics come from the evidence origin (D3).** Each ``ProcedureMaterialUse`` carries a source-authored
  :class:`~smartchem.material_spec.MaterialSpecification`; this module only PROJECTS it. A use whose raw
  ``formulation`` text is non-empty but whose ``specification`` is ``None`` projects as an UNRESOLVED term (F69) --
  an open question, never "no constraint". Phase comes ONLY from ``use.phase`` (one representation; nothing implies
  a phase from words).
* **Quantities never vanish (D1).** A requirement's ``quantity`` is a :class:`~.quantity.QuantityDemand` -- exact
  per-unit sums plus a COUNT of unquantified uses; mixed units keep both components; a leaf reactant nobody typed
  is an ``UNKNOWN`` (real, positive, unsized) demand.
* **A demand stated anywhere reaches its axis or that axis fails closed (D13).** Every raw ``op.materials`` string a
  typed use does not cover, every ``envelope.catalysts`` entry no CATALYST use covers, and an uncovered
  ``envelope.medium`` become name-keyed, UNRESOLVED requirements (never FIT); a balanced species with no hazard
  record is carried as hazard-unresolved; op/envelope temperatures, pressures and durations reach the physical and
  process axes; a hardware-demanding op that names no apparatus, an applied field, and a stated analytical
  verification with no measurement apparatus are carried as unrecognized (UNKNOWN) remainders.
* **Waste is derived by** :func:`smartchem.capability.waste.derive_waste` **(D9)** -- this module only packages it.

Nothing here decides FIT/BLOCKED/UNKNOWN -- that fold lives in :mod:`smartchem.capability.assess`.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule
from ..constraints import PhysicalBounds
from ..contracts import Digestible, canonical_digest
from ..data.reagents import Availability
from ..experiment.affordability import CostVector, basket_cost_vector
from ..experiment.catalyst_availability import catalyst_availability
from ..experiment.equipment import EquipmentKind, equipment_for_step
from ..experiment.handling import CareLevel, verify_handling
from ..experiment.step import ExperimentRoute
from ..experiment.stock import Phase
from ..material_spec import MaterialSpecification
from ..procedure_evidence import OperationKind, ProcedureMaterialRole
from ..process_constraints import ProcessRequirements
from .enums import ContainmentCapability, EquipmentCapability, MeasurementMethod, WasteCapability
from .equipment_resolver import classify_apparatus_strings
from .measurement_resolver import classify_measurement_strings
from .quantity import QuantityDemand

__all__ = [
    "MaterialRequirement",
    "WasteRequirement",
    "RouteCapabilityRequirements",
    "compile_capability_requirements",
]

_EMPTY_SPEC = MaterialSpecification()


@dataclass(frozen=True)
class MaterialRequirement(Digestible):
    """A REQUIREMENT-side object (never a second inventory): one material a route needs, keyed by canonical
    STRUCTURE (``identity``) or by declared NAME (``name``), with the source-projected gates:

    * ``specification`` -- what the SOURCE says the material must BE (composition on a stated basis, positively
      required states, unresolved load-bearing terms); empty = the source demanded nothing beyond identity;
    * ``phase`` -- the use's own declared phase, or ``None`` (never implied from words);
    * ``quantity`` -- the whole-route :class:`~.quantity.QuantityDemand`, NEVER ``None``;
    * ``untyped_source_text`` -- ``True`` when the only evidence is raw source text (an ``op.materials`` string, a
      catalyst or medium string no typed use covers): its ``name`` is that raw text, so ABSENCE under that key proves
      nothing (assess reads it as UNKNOWN, never BLOCKED) and its specification is unresolved (never FIT).
    """

    identity: "Molecule | None"
    phase: "Phase | None"
    quantity: QuantityDemand
    role: str
    evidence_source: str
    name: "str | None" = None
    specification: MaterialSpecification = _EMPTY_SPEC
    untyped_source_text: bool = False

    def __post_init__(self) -> None:
        if self.identity is not None and type(self.identity) is not Molecule:
            raise TypeError("identity must be a smartchem.category.Molecule or None")
        if self.name is not None:
            if not isinstance(self.name, str) or not self.name.strip():
                raise ValueError("name must be a non-empty string or None")
            object.__setattr__(self, "name", self.name.strip())
        if self.identity is None and self.name is None:
            raise ValueError("a material requirement needs at least one of identity (structure) or name")
        if self.phase is not None and type(self.phase) is not Phase:
            raise TypeError("phase must be a smartchem.experiment.stock.Phase or None")
        if type(self.quantity) is not QuantityDemand:
            raise TypeError("quantity must be a smartchem.capability.quantity.QuantityDemand (never None)")
        if type(self.specification) is not MaterialSpecification:
            raise TypeError("specification must be a smartchem.material_spec.MaterialSpecification")
        if type(self.untyped_source_text) is not bool:
            raise TypeError("untyped_source_text must be a bool")
        if self.untyped_source_text and not self.specification.unresolved_terms:
            raise ValueError("an untyped source-text requirement must carry an unresolved specification term")
        for attr in ("role", "evidence_source"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{attr} must be a non-empty string")
            object.__setattr__(self, attr, value.strip())

    @property
    def label(self) -> str:
        """A human label for reasons: the sourced name if any, else the structure repr."""
        return self.name if self.name is not None else repr(self.identity)


@dataclass(frozen=True)
class WasteRequirement(Digestible):
    """The waste-routing categories a route demands, the named facts that put them there, and the streams whose
    disposal routing could not be positively determined (``unresolved`` caps the waste axis at UNKNOWN)."""

    categories: "frozenset[WasteCapability]"
    reasons: "tuple[str, ...]"
    unresolved: "tuple[str, ...]" = ()

    def __post_init__(self) -> None:
        if type(self.categories) is not frozenset or any(
            type(c) is not WasteCapability for c in self.categories
        ):
            raise TypeError("categories must be a frozenset of WasteCapability values")
        for attr in ("reasons", "unresolved"):
            value = getattr(self, attr)
            if type(value) is not tuple or any(not isinstance(r, str) or not r.strip() for r in value):
                raise TypeError(f"{attr} must be a tuple of non-empty strings")


@dataclass(frozen=True)
class RouteCapabilityRequirements(Digestible):
    """The independent capability axes a route needs, PURELY projected from its own sourced evidence.
    ``route_digest`` ties this record back to the exact ``ExperimentRoute`` it was compiled from.

    ``equipment_unrecognized`` / ``measurement_unrecognized`` carry the fail-closed remainder (an untabled
    apparatus/measurement string, a hardware op that names no apparatus, an applied field, a stated analytical
    verification with no measurement apparatus) -> an assess-side UNKNOWN gate. ``hazard_unresolved`` carries every
    material whose hazard status could not be resolved (typed use, untyped source text, or balanced species with no
    hazard record). ``physical_unresolved`` / ``process_unresolved`` (D13) carry stated T/P/duration demands this
    projection could not read into the typed bounds (a non-canonical unit; a duration the process record's elapsed
    ceiling does not cover) -> those axes fail closed to UNKNOWN.
    """

    route_digest: str
    material: "tuple[MaterialRequirement, ...]"
    equipment: "frozenset[EquipmentCapability]"
    equipment_unrecognized: "tuple[str, ...]"
    physical: PhysicalBounds
    process: "tuple[ProcessRequirements | None, ...]"
    containment: "frozenset[ContainmentCapability]"
    containment_reasons: "tuple[str, ...]"
    hazard_unresolved: "tuple[str, ...]"
    measurement: "frozenset[MeasurementMethod]"
    measurement_unrecognized: "tuple[str, ...]"
    waste: WasteRequirement
    procurement_catalysts: "tuple[tuple[str, Availability | None], ...]"
    attention_care: CareLevel
    monetary: CostVector
    physical_unresolved: "tuple[str, ...]" = ()
    process_unresolved: "tuple[str, ...]" = ()

    def __post_init__(self) -> None:
        if not isinstance(self.route_digest, str) or not self.route_digest:
            raise ValueError("route_digest must be a non-empty string")
        if type(self.material) is not tuple or any(
            type(m) is not MaterialRequirement for m in self.material
        ):
            raise TypeError("material must be a tuple of MaterialRequirement values")
        if type(self.equipment) is not frozenset or any(
            type(e) is not EquipmentCapability for e in self.equipment
        ):
            raise TypeError("equipment must be a frozenset of EquipmentCapability values")
        for attr in ("equipment_unrecognized", "containment_reasons", "hazard_unresolved",
                     "measurement_unrecognized", "physical_unresolved", "process_unresolved"):
            value = getattr(self, attr)
            if type(value) is not tuple or any(not isinstance(s, str) or not s.strip() for s in value):
                raise TypeError(f"{attr} must be a tuple of non-empty strings")
        if type(self.physical) is not PhysicalBounds:
            raise TypeError("physical must be a smartchem.constraints.PhysicalBounds")
        if type(self.process) is not tuple or any(
            p is not None and type(p) is not ProcessRequirements for p in self.process
        ):
            raise TypeError("process must be a tuple of (ProcessRequirements | None)")
        if type(self.containment) is not frozenset or any(
            type(c) is not ContainmentCapability for c in self.containment
        ):
            raise TypeError("containment must be a frozenset of ContainmentCapability values")
        if type(self.measurement) is not frozenset or any(
            type(m) is not MeasurementMethod for m in self.measurement
        ):
            raise TypeError("measurement must be a frozenset of MeasurementMethod values")
        if type(self.waste) is not WasteRequirement:
            raise TypeError("waste must be a WasteRequirement")
        if type(self.procurement_catalysts) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0].strip()
            or (item[1] is not None and type(item[1]) is not Availability)
            for item in self.procurement_catalysts
        ):
            raise TypeError(
                "procurement_catalysts must be a tuple of (name: non-empty str, tier: Availability | None) pairs"
            )
        if type(self.attention_care) is not CareLevel:
            raise TypeError("attention_care must be a CareLevel")
        if type(self.monetary) is not CostVector:
            raise TypeError("monetary must be a CostVector")


# -- structure-identity + name-coverage helpers (pure, route-only) ---------------------------------------------

def _struct_digest(molecule: Molecule) -> str:
    """The canonical STRUCTURE digest of ``molecule`` -- the same isomer-proof key the stock layer uses. A molecule
    that cannot canonicalise falls back to its as-given digest (never a crash, never a false match)."""
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return canonical_digest(molecule)


def _norm_text(text: str) -> str:
    return " ".join(text.strip().casefold().split())


#: The use roles that represent a leaf reactant's stoichiometric charge (Wave-C nag: a wash never stands in).
_STOICHIOMETRIC_ROLES = frozenset({ProcedureMaterialRole.SUBSTRATE, ProcedureMaterialRole.REACTANT})


def _name_covers(use_name: str, raw: str) -> bool:
    """Does a typed use named ``use_name`` cover the raw source string ``raw``? Case/whitespace-folded EQUALITY only
    (Wave-C K4): a whole-word containment test let a raw string naming a SECOND species beside a typed name
    ("<other species> in <typed name>") vanish behind the typed use. The source author aligns ``op.materials`` with the typed names; any raw string that
    is not exactly a typed name is UNCOVERED and becomes an unresolved requirement (fail closed)."""
    name, text = _norm_text(use_name), _norm_text(raw)
    return bool(name) and name == text


def _project_specification(use) -> MaterialSpecification:
    """D3/F69: the use's source-authored specification; a non-empty raw formulation with NO typed specification is an
    UNRESOLVED term (UNKNOWN, never "no constraint"); otherwise the empty specification."""
    if use.specification is not None:
        return use.specification
    raw = (use.formulation or "").strip()
    if raw:
        return MaterialSpecification(unresolved_terms=(raw,))
    return _EMPTY_SPEC


def _untyped_source_materials(route: ExperimentRoute) -> "list[tuple[str, str]]":
    """D13 P0-1/P0-2: every raw material string the source states that NO typed use covers, as ``(raw, locator)``:
    each ``op.materials`` entry not covered by a use OF THAT OP, each ``envelope.catalysts`` entry not covered by a
    CATALYST use of that step, and a non-empty ``envelope.medium`` not covered by any use of that step. An op or step
    with no typed uses at all leaves every such string uncovered."""
    found: "list[tuple[str, str]]" = []
    for s_index, step in enumerate(route.steps, start=1):
        envelope = step.envelope
        procedure = envelope.procedure
        step_uses = [] if procedure is None else [u for op in procedure.operations for u in op.material_uses]
        if procedure is not None:
            for op in procedure.operations:
                for raw in op.materials:
                    if not any(_name_covers(u.name, raw) for u in op.material_uses):
                        found.append((raw, f"step {s_index} op {op.ordinal} {op.kind.value} materials"))
        catalyst_uses = [u for u in step_uses if u.role is ProcedureMaterialRole.CATALYST]
        for raw in envelope.catalysts:
            if not any(_name_covers(u.name, raw) for u in catalyst_uses):
                found.append((raw, f"step {s_index} envelope catalyst"))
        medium = (envelope.medium or "").strip()
        if medium and not any(_name_covers(u.name, medium) for u in step_uses):
            found.append((medium, f"step {s_index} envelope medium"))
    return found


def _material_requirements(route: ExperimentRoute) -> "tuple[MaterialRequirement, ...]":
    """ONE generic projection over every sourced ``ProcedureMaterialUse`` (D1/D3). Uses group by (species key,
    projected-specification digest, declared phase): same group -> ONE requirement whose quantity is the exact
    :meth:`QuantityDemand.combine` of every use's quantity (an unquantified use is COUNTED, never dropped); different
    specification or phase -> separate requirements (the allocator in assess still spends each bottle once).
    Then (D13) every uncovered raw material string becomes an untyped, unresolved, name-keyed requirement, and every
    leaf reactant no typed use covers earns a bare structure requirement with an ``UNKNOWN`` quantity."""
    groups: "dict[tuple, dict]" = {}
    order: "list[tuple]" = []
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                spec = _project_specification(use)
                species_key = (("struct", _struct_digest(use.identity)) if use.identity is not None
                               else ("name", _norm_text(use.name)))
                key = (species_key, canonical_digest(spec), use.phase)
                group = groups.get(key)
                if group is None:
                    group = {"identity": None, "names": set(), "roles": set(), "spec": spec, "phase": use.phase,
                             "quantities": [], "evidence": []}
                    groups[key] = group
                    order.append(key)
                group["names"].add(use.name)
                group["roles"].add(use.role)
                if group["identity"] is None and use.identity is not None:
                    group["identity"] = use.identity
                group["quantities"].append(use.quantity)
                if use.evidence_source not in group["evidence"]:
                    group["evidence"].append(use.evidence_source)
    projected_ids: "set[str]" = set()
    requirements: "list[MaterialRequirement]" = []
    for key in order:
        group = groups[key]
        name = min(group["names"], key=lambda n: (len(n.split()), len(n), n))
        roles = ", ".join(sorted(r.value for r in group["roles"]))
        # Wave-C nag: only a STOICHIOMETRIC typed use (SUBSTRATE/REACTANT) stands in for a leaf reactant's
        # consumption -- a 5 mL wash or a VERIFY sample of the same structure must never erase the charge.
        if group["identity"] is not None and group["roles"] & _STOICHIOMETRIC_ROLES:
            projected_ids.add(_struct_digest(group["identity"]))
        requirements.append(MaterialRequirement(
            identity=group["identity"], phase=group["phase"],
            quantity=QuantityDemand.combine(group["quantities"]),
            role=f"procedure material ({roles})",
            evidence_source="; ".join(group["evidence"]), name=name, specification=group["spec"],
        ))
    # D13: untyped raw source strings -- one requirement per distinct (folded) string, every occurrence counted.
    untyped: "dict[str, dict]" = {}
    for raw, locator in _untyped_source_materials(route):
        entry = untyped.setdefault(_norm_text(raw), {"raw": raw.strip(), "locators": []})
        entry["locators"].append(locator)
    for entry in untyped.values():
        requirements.append(MaterialRequirement(
            identity=None, phase=None, quantity=QuantityDemand.unstated(len(entry["locators"])),
            role="untyped source material",
            evidence_source=(
                f"raw source text at {', '.join(entry['locators'])} with no covering typed ProcedureMaterialUse -- "
                "identity, specification and quantity are all UNRESOLVED (D13; never FIT, never silently dropped)"),
            name=entry["raw"],
            specification=MaterialSpecification(unresolved_terms=(f"untyped source material: {entry['raw']}",)),
            untyped_source_text=True,
        ))
    for leaf in route.leaf_inputs:
        digest = _struct_digest(leaf)
        if digest not in projected_ids:
            projected_ids.add(digest)
            requirements.append(MaterialRequirement(
                identity=leaf, phase=None, quantity=QuantityDemand.unstated(1), role="reactant (leaf input)",
                evidence_source=(
                    "route leaf input (ExperimentRoute.leaf_inputs) with no typed source ProcedureMaterialUse -- the "
                    "identity is required and CONSUMED (a real, positive demand), but no specification/phase/quantity "
                    "is sourced, so those stay UNKNOWN (never assumed)"),
            ))
    return tuple(requirements)


#: D13 P0-4: op kinds that physically demand hardware. One of these naming NO apparatus is an unread equipment demand.
_HARDWARE_OP_KINDS = frozenset({
    OperationKind.HEAT, OperationKind.HOLD, OperationKind.COOL, OperationKind.DISTILL,
    OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY,
})


def _equipment_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[EquipmentCapability], tuple[str, ...]]":
    """The union, over every step, of sourced apparatus strings classified through the closed resolver -- NEVER
    ``equipment_for_step`` (F1). VERIFY ops are SKIPPED (their apparatus is a measurement method). Vetted consumables
    are dropped; untabled apparatus is carried forward. D13: a hardware op (heat/hold/cool/distill/separate/filter/dry)
    that names NO apparatus, and a declared applied field, are carried as unrecognized remainders (UNKNOWN)."""
    raw: "set[str]" = set()
    unread: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is not None:
            for op in procedure.operations:
                if op.kind is OperationKind.VERIFY:
                    continue
                raw.update(op.apparatus)
                if op.kind in _HARDWARE_OP_KINDS and not op.apparatus:
                    unread.append(f"step {s_index} op {op.ordinal} {op.kind.value} states no apparatus")
        process = step.envelope.process
        if process is not None and process.equipment is not None:
            raw.update(process.equipment)
        field_text = (step.envelope.applied_field or "").strip()
        if field_text:
            unread.append(f"step {s_index} applied field {field_text!r} has no equipment mapping")
    recognized, _ignored_consumables, unrecognized = classify_apparatus_strings(raw)
    return recognized, tuple(sorted(set(unrecognized) | set(unread)))


def _measurement_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[MeasurementMethod], tuple[str, ...]]":
    """The SPECIFIC :class:`MeasurementMethod` set the route's VERIFY ops demand, plus the untabled remainder. D13: a
    procedure whose ``analytical_verification`` is PRESENT but whose VERIFY ops name no apparatus is an unread
    measurement demand -> carried as unrecognized (UNKNOWN)."""
    raw: "set[str]" = set()
    unread: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        verify_apparatus: "set[str]" = set()
        for op in procedure.operations:
            if op.kind is OperationKind.VERIFY:
                verify_apparatus.update(op.apparatus)
        raw.update(verify_apparatus)
        if procedure.analytical_verification.is_present and not verify_apparatus:
            unread.append(f"step {s_index} states an analytical verification but no VERIFY op names its apparatus")
    recognized, _ignored, unrecognized = classify_measurement_strings(raw)
    return recognized, tuple(unrecognized) + tuple(sorted(unread))


def _hazard_scan(
    route: ExperimentRoute, untyped: "list[tuple[str, str]]",
) -> "tuple[bool, tuple[str, ...], tuple[str, ...]]":
    """Fold material hazards into containment. Returns ``(forces_containment, containment_reasons,
    hazard_unresolved)``. Three sources, one law (a real GHS record forces containment; NO record is UNRESOLVED;
    an empty-GHS record forces nothing):

    * every typed ``ProcedureMaterialUse`` (structure lookup first, then the sourced name);
    * every untyped raw source material string (D13, by name only);
    * every BALANCED species of every step (D13 P0-2b: parity with the typed path -- a reactant/product with no
      hazard record is unresolved, never silently skipped).
    """
    from ..decompiler_review import molecule_hazards  # lazy: mirrors equipment.py, breaks the import cycle
    from ..data.hazards import hazards_for_named

    forces = False
    reasons: "list[str]" = []
    unresolved: "list[str]" = []
    seen: "set[str]" = set()

    def _fold(label: str, hazard, unresolved_note: str) -> None:
        nonlocal forces
        if hazard is not None and hazard.ghs_codes:
            forces = True
            reasons.append(f"containment: {label} carries sourced GHS {', '.join(hazard.ghs_codes)} ({hazard.name}) "
                           "-- forces FUME_HOOD (inform, never neuter)")
        elif hazard is None:
            unresolved.append(f"containment: {label} -- {unresolved_note}; its hazard status is UNKNOWN (not a safety "
                              "clearance; CAPABILITY_FIT is not a safety cert)")

    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                key = _struct_digest(use.identity) if use.identity is not None else f"name:{_norm_text(use.name)}"
                if key in seen:
                    continue
                seen.add(key)
                hazard = molecule_hazards(use.identity) if use.identity is not None else None
                if hazard is None:
                    hazard = hazards_for_named(use.name)
                kind = "an unresolvable ionic/mixture species" if use.identity is None else "no GHS record"
                _fold(f"procedure-only {use.name!r} ({use.role.value})", hazard, kind)
    for raw, locator in untyped:
        key = f"untyped:{_norm_text(raw)}"
        if key in seen:
            continue
        seen.add(key)
        _fold(f"untyped source material {raw.strip()!r} ({locator})", hazards_for_named(raw.strip()),
              "raw source text with no typed identity and no hazard record")
    for s_index, step in enumerate(route.steps, start=1):
        for molecule in (*step.reactants, *step.products):
            key = _struct_digest(molecule)
            if key in seen:
                continue
            seen.add(key)
            _fold(f"balanced species {molecule!r} (step {s_index})", molecule_hazards(molecule),
                  "no hazard record for this structure")
    return forces, tuple(reasons), tuple(unresolved)


def _containment_requirement(
    route: ExperimentRoute, material_forces: bool,
) -> "frozenset[ContainmentCapability]":
    """ONLY hazard-driven ``CONTAINMENT``-kind items: the balanced lane via ``equipment_for_step``, PLUS a resolved
    material hazard from :func:`_hazard_scan`. The reachable member is ``FUME_HOOD``."""
    for step in route.steps:
        for item in equipment_for_step(step):
            if item.kind is EquipmentKind.CONTAINMENT:
                return frozenset({ContainmentCapability.FUME_HOOD})
    if material_forces:
        return frozenset({ContainmentCapability.FUME_HOOD})
    return frozenset()


def _interval_of(field) -> "object | None":
    """The ``Interval`` value of a PRESENT procedure ``EvidenceField``, else ``None`` (a string value is prose)."""
    from ..conditions import Interval

    if field is None or not field.is_present or not isinstance(field.value, Interval):
        return None
    return field.value


def _physical_requirement(route: ExperimentRoute) -> "tuple[PhysicalBounds, tuple[str, ...]]":
    """D13 P0-4: the route's T/P extrema read from EVERY place a step states them -- ``ProcessRequirements``, the
    envelope's temperature/pressure intervals, and every op temperature/pressure ``Interval`` -- the MAX peak
    temperature, MAX max-pressure and MIN min-pressure (never an ``elif`` that lets the smaller one win). An interval
    in a unit other than K (temperature) / atm (pressure) is carried as unresolved -> physical UNKNOWN."""
    peaks: "list[float]" = []
    min_pressures: "list[float]" = []
    max_pressures: "list[float]" = []
    unresolved: "list[str]" = []

    def _temperature(interval, where: str) -> None:
        if interval is None:
            return
        if interval.unit != "K":
            unresolved.append(f"{where} temperature stated in {interval.unit!r}, not K -- unread (no unit engine)")
            return
        peaks.append(interval.hi)

    def _pressure(interval, where: str) -> None:
        if interval is None:
            return
        if interval.unit != "atm":
            unresolved.append(f"{where} pressure stated in {interval.unit!r}, not atm -- unread (no unit engine)")
            return
        min_pressures.append(interval.lo)
        max_pressures.append(interval.hi)

    for s_index, step in enumerate(route.steps, start=1):
        envelope = step.envelope
        process = envelope.process
        if process is not None:
            if process.peak_temperature_k is not None:
                peaks.append(process.peak_temperature_k)
            if process.min_pressure_atm is not None:
                min_pressures.append(process.min_pressure_atm)
            if process.max_pressure_atm is not None:
                max_pressures.append(process.max_pressure_atm)
        _temperature(envelope.temperature, f"step {s_index} envelope")
        _pressure(envelope.pressure, f"step {s_index} envelope")
        if envelope.procedure is not None:
            for op in envelope.procedure.operations:
                where = f"step {s_index} op {op.ordinal} {op.kind.value}"
                _temperature(_interval_of(op.temperature), where)
                _pressure(_interval_of(op.pressure), where)
                # D13 (parent integration): a PROSE-only op temperature/pressure ("reflux", "cool to room
                # temperature") cannot be compared -- it counts as READ only when the same step's authored process
                # record carries the numeric extremum for that dimension; otherwise it is an unread demand -> UNKNOWN.
                has_peak = process is not None and process.peak_temperature_k is not None
                has_pressure = process is not None and (
                    process.max_pressure_atm is not None or process.min_pressure_atm is not None)
                for label, field, covered in (("temperature", op.temperature, has_peak),
                                              ("pressure", op.pressure, has_pressure)):
                    if (field is not None and field.is_present and _interval_of(field) is None
                            and not covered):
                        unresolved.append(
                            f"{where} states its {label} only in prose ({field.value!r}) and step {s_index}'s "
                            f"process record carries no numeric {label} -- an unread demand (D13)")
    bounds = PhysicalBounds.of(
        max_temperature_k=max(peaks) if peaks else None,
        min_pressure_atm=min(min_pressures) if min_pressures else None,
        max_pressure_atm=max(max_pressures) if max_pressures else None,
    )
    return bounds, tuple(unresolved)


def _process_unresolved(route: ExperimentRoute) -> "tuple[str, ...]":
    """D13 P0-4: a duration stated OUTSIDE the process record (``envelope.duration`` or an op duration ``Interval``)
    must be covered by that step's process elapsed CEILING, or the process axis cannot certify it -> UNKNOWN."""
    out: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        envelope = step.envelope
        stated: "list[tuple[str, object]]" = []
        if envelope.duration is not None:
            stated.append(("envelope duration", envelope.duration))
        if envelope.procedure is not None:
            for op in envelope.procedure.operations:
                interval = _interval_of(op.duration)
                if interval is not None:
                    stated.append((f"op {op.ordinal} {op.kind.value} duration", interval))
        if not stated:
            continue
        minutes: "list[float]" = []
        for where, interval in stated:
            if interval.unit != "min":
                out.append(f"step {s_index} {where} stated in {interval.unit!r}, not min -- unread (no unit engine)")
            else:
                minutes.append(interval.hi)
        if not minutes:
            continue
        longest = max(minutes)
        process = envelope.process
        ceiling = None if process is None or process.elapsed_minutes is None else process.elapsed_minutes.hi
        if ceiling is None or ceiling < longest:
            covered = "no process record" if process is None else (
                "no process elapsed ceiling" if ceiling is None else f"a process elapsed ceiling of {ceiling:g} min")
            out.append(f"step {s_index}: a duration of {longest:g} min is stated outside the process record, which "
                       f"has {covered} -- the process axis cannot certify it")
    return tuple(out)


def _waste_requirement(route: ExperimentRoute) -> WasteRequirement:
    """D9: waste classification is owned by :func:`smartchem.capability.waste.derive_waste` (categories earned only
    from positive stream evidence; residuals and operation-derived spent streams unresolved). Packaged here."""
    from .waste import derive_waste  # lazy: the waste module reads route-level handling/procedure facts

    categories, reasons, unresolved = derive_waste(route)
    return WasteRequirement(frozenset(categories), tuple(reasons), tuple(unresolved))


def _procurement_catalysts_requirement(
    route: ExperimentRoute,
) -> "tuple[tuple[str, Availability | None], ...]":
    """One ``(name, tier)`` pair per catalyst the route DECLARES -- every ``envelope.catalysts`` entry AND (D13) every
    typed CATALYST use not already listed -- deduplicated case-insensitively, ``tier`` resolved through the UNMODIFIED
    ``catalyst_availability`` classifier (``None`` = honest UNRECOGNIZED)."""
    seen: "dict[str, tuple[str, Availability | None]]" = {}
    for step in route.steps:
        names = list(step.envelope.catalysts)
        procedure = step.envelope.procedure
        if procedure is not None:
            names.extend(u.name for op in procedure.operations for u in op.material_uses
                         if u.role is ProcedureMaterialRole.CATALYST)
        for cat in names:
            key = _norm_text(cat)
            if key and key not in seen:
                seen[key] = (cat, catalyst_availability(cat))
    return tuple(seen.values())


def compile_capability_requirements(route: ExperimentRoute) -> RouteCapabilityRequirements:
    """The PURE projection: what does ``route``'s own sourced evidence require, on every capability axis?

    Reads ONLY ``route`` -- never a :class:`~smartchem.capability.profile.CapabilityProfile`, never a named preset,
    never the network. Nothing here decides FIT/BLOCKED/UNKNOWN.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")

    equipment, equipment_unrecognized = _equipment_requirement(route)
    measurement, measurement_unrecognized = _measurement_requirement(route)
    untyped = _untyped_source_materials(route)
    material_forces, containment_reasons, hazard_unresolved = _hazard_scan(route, untyped)
    physical, physical_unresolved = _physical_requirement(route)
    handling_care = verify_handling(route).care

    return RouteCapabilityRequirements(
        route_digest=route.digest,
        material=_material_requirements(route),
        equipment=equipment,
        equipment_unrecognized=equipment_unrecognized,
        physical=physical,
        process=tuple(step.envelope.process for step in route.steps),
        containment=_containment_requirement(route, material_forces),
        containment_reasons=containment_reasons,
        hazard_unresolved=hazard_unresolved,
        measurement=measurement,
        measurement_unrecognized=measurement_unrecognized,
        waste=_waste_requirement(route),
        procurement_catalysts=_procurement_catalysts_requirement(route),
        attention_care=handling_care,
        monetary=basket_cost_vector(list(route.leaf_inputs)),
        physical_unresolved=physical_unresolved,
        process_unresolved=_process_unresolved(route),
    )
