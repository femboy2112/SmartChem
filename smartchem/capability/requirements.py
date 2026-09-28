"""smartchem/capability/requirements.py -- the PURE requirement projection (Round III, D1-D9).

**Look at me, I'm a Meeseeks who only ever ASKS questions!** ``compile_capability_requirements`` reads
ONE ``ExperimentRoute`` and answers, axis by axis, "what does the sourced evidence say THIS route needs?"
-- and it is FORBIDDEN, on pain of not being the projection the FREEZE describes, from ever peeking at a
``CapabilityProfile`` to answer that question. A requirement compiled here has no idea whether anyone's
bench can meet it; that verdict is a whole separate Meeseeks's job (:mod:`smartchem.capability.assess`).

Round III burned down two Round-II lies of convenience and lit the replacements:

* **The universal esterification assay floor is DEAD (D1, kills M23).** No reaction-CLASS label may ever
  manufacture a material assay. Assay/formulation/quantity requirements are now SOURCE-scoped per input:
  the acetic-acid leaf earns a ``glacial`` compendial formulation (``Phase.LIQUID`` + a DERIVED_WITH_ERROR
  >=0.99 floor + the sourced 20 mL draw) ONLY when this route's own sourced procedure names "glacial", and
  the isoamyl-alcohol leaf earns a neat ``Phase.LIQUID`` requirement (assay ``None`` -- phase is the honest
  compatibility mechanism, never a fabricated number). Any other leaf, or an unsourced route, keeps the
  honest ``required_assay=None`` / ``phase=None``.
* **Procedure-only species no longer vanish (D2, kills M24/M6-adjacent).** ``ProcedureOperation.material_uses``
  -- the H2SO4 catalyst, the NaHCO3/NaCl/MgSO4 washes+drier, the water -- are projected into the SAME
  material axis (matched by structure identity where it resolves, by declared NAME where it is an ionic
  lattice) AND their resolved GHS hazards feed the containment axis (D9). A procedure material is NEVER
  silently dropped: an unresolvable/no-GHS one is carried in ``hazard_unresolved`` and surfaced, never
  faked into a containment requirement out of ignorance.
* **Measurement is live (D5, kills M27/M28).** Every ``VERIFY`` op's ``apparatus`` is classified through the
  closed :mod:`.measurement_resolver` into SPECIFIC :class:`MeasurementMethod` members (never the coarse
  tier); an untabled string is carried in ``measurement_unrecognized`` for the assess-side UNKNOWN gate.
  VERIFY ops are skipped by the EQUIPMENT axis -- their apparatus is a measurement fact, not glassware.

Every other axis reads a fact that ALREADY EXISTS on the route -- never new physics, never a fabricated
threshold. Nothing here decides FIT/BLOCKED/UNKNOWN -- that fold lives in :mod:`smartchem.capability.assess`.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule
from ..contracts import Digestible, canonical_digest
from ..data.reagents import Availability
from ..experiment.affordability import CostVector, basket_cost_vector
from ..experiment.catalyst_availability import catalyst_availability
from ..experiment.equipment import EquipmentKind, equipment_for_step
from ..experiment.handling import CareLevel, verify_handling
from ..experiment.step import ExperimentRoute
from ..experiment.stock import Phase, StockQuantity
from ..procedure_evidence import OperationKind
from ..constraints import PhysicalBounds
from ..process_constraints import ProcessRequirements
from .enums import ContainmentCapability, EquipmentCapability, MeasurementMethod, WasteCapability
from .equipment_resolver import classify_apparatus_strings
from .measurement_resolver import classify_measurement_strings

__all__ = [
    "MaterialRequirement",
    "WasteRequirement",
    "RouteCapabilityRequirements",
    "compile_capability_requirements",
]


@dataclass(frozen=True)
class MaterialRequirement(Digestible):
    """A REQUIREMENT-side object (never a second inventory -- D1): one material a route needs, keyed by
    canonical STRUCTURE (``identity``) OR by declared NAME (``name``, for an ionic/mixture species that
    honestly cannot resolve to a covalent :class:`~smartchem.category.Molecule`), plus the source-scoped
    assay / phase / quantity gates -- each ``None`` when the source states nothing (never assumed).

    ``identity`` is ``Molecule | None`` and ``name`` is ``str | None``, mirroring the honesty pattern the
    stock layer already carries (``required_assay: float | None``): at least ONE must be set, and a
    requirement may carry BOTH (a structure-resolvable procedure material still keeps its sourced name so it
    can be matched against a NAME-keyed declared stock bottle -- water is exactly this). ``required_assay``,
    ``phase`` and ``quantity`` are the three independent gates :mod:`smartchem.capability.assess` combines;
    all three ``None`` means possession-only, which is an honest UNKNOWN, never a silent FIT.
    """

    identity: "Molecule | None"
    required_assay: "float | None"
    phase: "Phase | None"
    quantity: "StockQuantity | None"
    role: str
    evidence_source: str
    name: "str | None" = None

    def __post_init__(self) -> None:
        if self.identity is not None and type(self.identity) is not Molecule:
            raise TypeError("identity must be a smartchem.category.Molecule or None")
        if self.name is not None:
            if not isinstance(self.name, str) or not self.name.strip():
                raise ValueError("name must be a non-empty string or None")
            object.__setattr__(self, "name", self.name.strip())
        if self.identity is None and self.name is None:
            raise ValueError("a material requirement needs at least one of identity (structure) or name")
        if self.required_assay is not None:
            if isinstance(self.required_assay, bool) or not isinstance(self.required_assay, (int, float)):
                raise TypeError("required_assay must be a real number or None (UNKNOWN)")
            if not (0.0 < float(self.required_assay) <= 1.0):
                raise ValueError("required_assay must be a fraction in (0, 1] or None (UNKNOWN)")
            object.__setattr__(self, "required_assay", float(self.required_assay))
        if self.phase is not None and type(self.phase) is not Phase:
            raise TypeError("phase must be a smartchem.experiment.stock.Phase or None")
        if self.quantity is not None and type(self.quantity) is not StockQuantity:
            raise TypeError("quantity must be a smartchem.experiment.stock.StockQuantity or None")
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
    """The waste-routing categories a route's byproduct/off-gas ledger demands, plus the named facts that
    put them there (derived from ``RouteHandling.all_byproducts``/``all_offgases`` + ``Fate``, never
    ``CostVector.waste_disposal``). An empty ``categories`` means no waste-routing obligation was derived."""

    categories: "frozenset[WasteCapability]"
    reasons: "tuple[str, ...]"

    def __post_init__(self) -> None:
        if type(self.categories) is not frozenset or any(
            type(c) is not WasteCapability for c in self.categories
        ):
            raise TypeError("categories must be a frozenset of WasteCapability values")
        if type(self.reasons) is not tuple or any(
            not isinstance(r, str) or not r.strip() for r in self.reasons
        ):
            raise TypeError("reasons must be a tuple of non-empty strings")


@dataclass(frozen=True)
class RouteCapabilityRequirements(Digestible):
    """The independent capability axes a route needs, PURELY projected from its own sourced evidence.
    ``route_digest`` ties this record back to the exact ``ExperimentRoute`` it was compiled from.

    ``equipment_unrecognized`` / ``measurement_unrecognized`` carry the closed resolvers' fail-closed
    remainder (an untabled apparatus/measurement string -> an assess-side UNKNOWN gate, never a silent
    pass). ``hazard_unresolved`` (D9) carries every procedure-only auxiliary whose hazard status could not
    be resolved (ionic/no-GHS): surfaced in the containment/waste axis reasons, never faked into a
    containment requirement out of ignorance, never forcing overall UNKNOWN (CAPABILITY_FIT is explicitly
    NOT a safety certificate). ``containment_reasons`` names the RESOLVED procedure-material hazards that DO
    force containment (H2SO4 -> H314 -> FUME_HOOD), so the fold is observable, not silent.
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
                     "measurement_unrecognized"):
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


# -- structure-identity helpers (pure, route-only) ------------------------------------------------------------

def _struct_digest(molecule: Molecule) -> str:
    """The canonical STRUCTURE digest of ``molecule`` -- the same isomer-proof key the stock layer uses to
    match a requirement against a declared bottle. A molecule that cannot canonicalise falls back to its
    as-given digest (never a crash, never a false match onto a different structure)."""
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return canonical_digest(molecule)


_KNOWN_LEAF_IDS: "dict[str, str] | None" = None


def _known_leaf_ids() -> "dict[str, str]":
    """The canonical structure digests of the two source-scoped reagent leaves (acetic acid, isoamyl
    alcohol), resolved through the SAME name-resolution path the search and the stock library use so the
    keys are byte-identical. Lazily computed + cached to keep this module free of an import-time cycle."""
    global _KNOWN_LEAF_IDS
    if _KNOWN_LEAF_IDS is None:
        from ..identity_parse import InputKind, resolve_target
        _KNOWN_LEAF_IDS = {
            "acetic_acid": _struct_digest(resolve_target("acetic acid", InputKind.NAME).canonical()),
            "isoamyl": _struct_digest(resolve_target("isoamyl alcohol", InputKind.NAME).canonical()),
        }
    return _KNOWN_LEAF_IDS


#: DERIVED_WITH_ERROR glacial-acetic floor (D1): USP/ACS "glacial acetic acid" is a compendial FORMULATION
#: (>=99% mass fraction). This floor is source-scoped -- it attaches to the acetic-acid leaf ONLY when THIS
#: route's own sourced procedure names "glacial", never to the reaction class (that was M23, now dead).
_GLACIAL_ACETIC_ASSAY = 0.99
_GLACIAL_ACETIC_EVIDENCE = (
    "DERIVED_WITH_ERROR: this route's sourced procedure names 'glacial acetic acid', a USP/ACS compendial "
    "FORMULATION (a neat Phase.LIQUID reagent, >=99% mass fraction). The requirement is source-scoped to the "
    "sourced word, NOT to the reaction class -- phase discriminates glacial from vinegar, assay reinforces it."
)
_ISOAMYL_NEAT_EVIDENCE = (
    "source-scoped: the sourced procedure names a NEAT isoamyl (isopentyl) alcohol reagent with no numeric "
    "purity, so compatibility is PHASE (Phase.LIQUID), required_assay stays None (never a fabricated number)."
)
_UNSOURCED_LEAF_EVIDENCE = (
    "route leaf input (ExperimentRoute.leaf_inputs); no source-scoped assay/phase requirement applies -- "
    "required_assay/phase stay UNKNOWN, never assumed 100% and never a fabricated phase"
)


def _sourced_procedure_text(route: ExperimentRoute) -> str:
    """The lowercased concatenation of THIS route's sourced procedure evidence strings (scale + per-op
    quantity/rate/endpoint). Used ONLY as the source-scope gate for the glacial formulation -- a light
    presence check for the compendial word, never a runtime parse of a quantity value into a requirement."""
    parts: "list[str]" = []
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        scale = procedure.scale
        if scale is not None and isinstance(scale.value, str):
            parts.append(scale.value)
        for op in procedure.operations:
            for field in (op.quantity, op.rate, op.endpoint):
                if field is not None and isinstance(field.value, str):
                    parts.append(field.value)
    return " ".join(parts).casefold()


def _route_is_sourced(route: ExperimentRoute) -> bool:
    """True iff this route carries at least one accepted-source procedure -- the source-scope gate for the
    per-leaf reactant volumes (D3): an unsourced route earns no authored quantity requirement."""
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is not None and procedure.is_sourced:
            return True
    return False


def _material_requirements(route: ExperimentRoute) -> "tuple[MaterialRequirement, ...]":
    """Leaf-reactant requirements (source-scoped per D1/D3) PLUS procedure-only requirements (D2). The
    retired esterification class floor is GONE -- no reaction-class label sets an assay here anymore."""
    text = _sourced_procedure_text(route)
    ids = _known_leaf_ids()
    sourced = _route_is_sourced(route)
    requirements: "list[MaterialRequirement]" = []
    for leaf in route.leaf_inputs:
        digest = _struct_digest(leaf)
        if sourced and digest == ids["acetic_acid"] and "glacial" in text:
            # D1 option B: the sourced 'glacial' compendial formulation -> Phase.LIQUID + >=0.99 assay + the
            # sourced 20 mL draw (D3). Vinegar BLOCKS on phase AND assay; glacial FITs. Gate #18, preserved.
            requirements.append(MaterialRequirement(
                identity=leaf, required_assay=_GLACIAL_ACETIC_ASSAY, phase=Phase.LIQUID,
                quantity=StockQuantity.of("20", "mL"), role="reactant (glacial acetic acid)",
                evidence_source=_GLACIAL_ACETIC_EVIDENCE,
            ))
        elif sourced and digest == ids["isoamyl"]:
            # D1 option C: neat reagent, compatibility by PHASE, assay honestly None. The 15 mL draw is the
            # sourced cleanly-separable reactant volume (D3).
            requirements.append(MaterialRequirement(
                identity=leaf, required_assay=None, phase=Phase.LIQUID,
                quantity=StockQuantity.of("15", "mL"), role="reactant (neat isoamyl alcohol)",
                evidence_source=_ISOAMYL_NEAT_EVIDENCE,
            ))
        else:
            requirements.append(MaterialRequirement(
                identity=leaf, required_assay=None, phase=None, quantity=None,
                role="reactant", evidence_source=_UNSOURCED_LEAF_EVIDENCE,
            ))
    requirements.extend(_procedure_only_material_requirements(route))
    return tuple(requirements)


def _procedure_only_material_requirements(
    route: ExperimentRoute,
) -> "tuple[MaterialRequirement, ...]":
    """Project every ``ProcedureOperation.material_uses`` auxiliary (catalyst/wash/drier/rinse/...) into the
    ONE material axis (D2, kills M24). Deduplicated by structure key (where identity resolves) or normalized
    name (ionic lattice): a species charged by two ops costs ONE requirement. A structure-resolvable
    auxiliary keeps BOTH its identity (for a structure-keyed bottle, e.g. H2SO4) AND its sourced name (for a
    NAME-keyed bottle, e.g. water) -- the assess side tries both. NEVER silently dropped."""
    groups: "dict[tuple[str, str], dict]" = {}
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                if use.identity is not None:
                    key = ("struct", _struct_digest(use.identity))
                else:
                    key = ("name", use.name.strip().casefold())
                group = groups.get(key)
                if group is None:
                    group = {
                        "identity": None, "names": set(), "roles": set(),
                        "formulation": None, "phase": None, "quantity": None, "evidence": use.evidence_source,
                    }
                    groups[key] = group
                group["names"].add(use.name)
                group["roles"].add(use.role)
                if group["identity"] is None and use.identity is not None:
                    group["identity"] = use.identity
                if group["formulation"] is None and use.formulation is not None:
                    group["formulation"] = use.formulation
                if group["phase"] is None and use.phase is not None:
                    group["phase"] = use.phase
                if group["quantity"] is None and use.quantity is not None:
                    group["quantity"] = use.quantity
    requirements: "list[MaterialRequirement]" = []
    for group in groups.values():
        # the bare head label (fewest tokens, then lexical) is the name a NAME-keyed bottle is stocked under
        # ("water", not "cold water") -- deterministic, never a fuzzy synonym match.
        name = min(group["names"], key=lambda n: (len(n.split()), len(n), n))
        roles = ", ".join(sorted(r.value for r in group["roles"]))
        requirements.append(MaterialRequirement(
            identity=group["identity"],
            required_assay=None,  # no procedure auxiliary in this corpus sources a numeric purity floor
            phase=group["phase"],
            quantity=group["quantity"],
            role=f"procedure-only auxiliary ({roles})",
            evidence_source=group["evidence"],
            name=name,
        ))
    return tuple(requirements)


def _equipment_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[EquipmentCapability], tuple[str, ...]]":
    """The union, over every step, of sourced apparatus strings classified through the closed resolver --
    NEVER ``equipment_for_step`` (F1). VERIFY ops are SKIPPED (D5): their apparatus is a MEASUREMENT method
    ("analytical balance", "infrared spectrometer"), not glassware, and belongs to the measurement axis.
    Vetted consumables are dropped (the whitelist is their trace); untabled apparatus is carried forward."""
    raw: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is not None:
            for op in procedure.operations:
                if op.kind is OperationKind.VERIFY:
                    continue  # D5: VERIFY apparatus is a measurement method, not equipment
                raw.update(op.apparatus)
        process = step.envelope.process
        if process is not None and process.equipment is not None:
            raw.update(process.equipment)
    recognized, _ignored_consumables, unrecognized = classify_apparatus_strings(raw)
    return recognized, tuple(sorted(unrecognized))


def _measurement_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[MeasurementMethod], tuple[str, ...]]":
    """The SPECIFIC :class:`MeasurementMethod` set the route's VERIFY ops demand (D5, kills M27/M28), plus
    the untabled remainder for the assess-side UNKNOWN gate. Reads ``op.apparatus`` on VERIFY ops ONLY --
    the exact strings the equipment axis now skips -- through the closed :mod:`.measurement_resolver`."""
    raw: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            if op.kind is OperationKind.VERIFY:
                raw.update(op.apparatus)
    recognized, _ignored, unrecognized = classify_measurement_strings(raw)
    return recognized, tuple(unrecognized)


def _procedure_hazard_scan(
    route: ExperimentRoute,
) -> "tuple[bool, tuple[str, ...], tuple[str, ...]]":
    """D9: fold procedure-only material hazards. Returns ``(forces_containment, containment_reasons,
    hazard_unresolved)``. A RESOLVED-identity auxiliary with a real GHS record forces containment (H2SO4 ->
    H314 -> FUME_HOOD) and is named in ``containment_reasons`` so the fold is observable even when the
    balanced lane already forced a hood. An UNRESOLVABLE (identity=None) or no-GHS auxiliary is carried in
    ``hazard_unresolved`` -- surfaced, never a fabricated containment requirement, never an overall UNKNOWN
    (CAPABILITY_FIT is not a safety cert). A resolved BENIGN species (water, empty GHS profile) is neither."""
    from ..decompiler_review import molecule_hazards  # lazy: mirrors equipment.py, breaks the import cycle
    from ..data.hazards import hazards_for_named

    forces = False
    reasons: "list[str]" = []
    unresolved: "list[str]" = []
    seen: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                dedupe_key = _struct_digest(use.identity) if use.identity is not None \
                    else f"name:{use.name.strip().casefold()}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                # Structure lookup first (the balanced lane's path); fall back to the SOURCED NAME (authored
                # evidence, not runtime prose) -- the H2SO4 catalyst has a valid Molecule identity but
                # ``molecule_name`` cannot name that SMILES, so its H314 GHS record is only reachable by the
                # sourced "sulfuric acid" name. Both are hazards.py lookups; neither invents a hazard.
                hazard = molecule_hazards(use.identity) if use.identity is not None else None
                if hazard is None:
                    hazard = hazards_for_named(use.name)
                if hazard is not None and hazard.ghs_codes:
                    forces = True
                    codes = ", ".join(hazard.ghs_codes)
                    reasons.append(
                        f"containment: procedure-only {use.name!r} ({use.role.value}) carries sourced GHS "
                        f"{codes} ({hazard.name}) -- forces FUME_HOOD (inform, never neuter)"
                    )
                elif hazard is None:
                    kind = "an unresolvable ionic/mixture species" if use.identity is None else "no GHS record"
                    unresolved.append(
                        f"containment: procedure-only {use.name!r} ({use.role.value}) -- {kind}; its hazard "
                        "status is UNKNOWN (not a safety clearance; CAPABILITY_FIT is not a safety cert)"
                    )
                # a resolved, positively-benign species (empty GHS profile, e.g. water) forces nothing.
    return forces, tuple(reasons), tuple(unresolved)


def _containment_requirement(
    route: ExperimentRoute, procedure_forces: bool,
) -> "frozenset[ContainmentCapability]":
    """ONLY hazard-driven ``CONTAINMENT``-kind items (F-nag's two-lanes rule): the balanced lane via
    ``equipment_for_step``, PLUS (D9) a resolved procedure-only material hazard (``procedure_forces``). The
    reachable member is ``FUME_HOOD``. Containment reads HAZARDS, never apparatus tuples."""
    for step in route.steps:
        for item in equipment_for_step(step):
            if item.kind is EquipmentKind.CONTAINMENT:
                return frozenset({ContainmentCapability.FUME_HOOD})
    if procedure_forces:
        return frozenset({ContainmentCapability.FUME_HOOD})
    return frozenset()


def _physical_requirement(route: ExperimentRoute) -> PhysicalBounds:
    """The route's own T/P extrema (a DEMAND), read off ``ProcessRequirements`` first and the envelope's
    declared temperature interval as a fallback."""
    peaks: "list[float]" = []
    min_pressures: "list[float]" = []
    max_pressures: "list[float]" = []
    for step in route.steps:
        process = step.envelope.process
        if process is not None and process.peak_temperature_k is not None:
            peaks.append(process.peak_temperature_k)
        elif step.envelope.temperature is not None:
            peaks.append(step.envelope.temperature.hi)
        if process is not None:
            if process.min_pressure_atm is not None:
                min_pressures.append(process.min_pressure_atm)
            if process.max_pressure_atm is not None:
                max_pressures.append(process.max_pressure_atm)
    return PhysicalBounds.of(
        max_temperature_k=max(peaks) if peaks else None,
        min_pressure_atm=min(min_pressures) if min_pressures else None,
        max_pressure_atm=max(max_pressures) if max_pressures else None,
    )


def _waste_requirement(route: ExperimentRoute) -> WasteRequirement:
    """Waste-routing categories derived from the sourced byproduct ledger + ``Fate`` (unchanged from Round
    II): an off-gas needs ``OFFGAS_CAPTURE``; a real-GHS byproduct needs ``HAZARDOUS``; a benign/unassessed
    condensed byproduct routes ``AQUEOUS_NEUTRAL``. Procedure-only hazards feed CONTAINMENT (D9), not this
    axis -- so the FIT positive's waste stays the sourced ``{AQUEOUS_NEUTRAL}`` shape."""
    handling = verify_handling(route)
    ghs_codes_by_name: "dict[str, tuple[str, ...]]" = {
        hazard.name: hazard.ghs_codes for step_handling in handling.steps for hazard in step_handling.hazards
    }
    categories: "set[WasteCapability]" = set()
    reasons: "list[str]" = []
    for b in handling.all_byproducts:
        is_real_hazard = b.hazard_name is not None and bool(ghs_codes_by_name.get(b.hazard_name))
        if b.is_offgas:
            categories.add(WasteCapability.OFFGAS_CAPTURE)
            reasons.append(f"waste: {b.molecule!r} evolves as an off-gas ({b.reason}) -- needs OFFGAS_CAPTURE")
            if is_real_hazard:
                categories.add(WasteCapability.HAZARDOUS)
                reasons.append(f"waste: off-gas {b.molecule!r} carries a real sourced hazard ({b.hazard_name})")
        elif is_real_hazard:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.append(f"waste: condensed byproduct {b.molecule!r} carries a real sourced hazard ({b.hazard_name})")
        else:
            categories.add(WasteCapability.AQUEOUS_NEUTRAL)
            reasons.append(
                f"waste: condensed byproduct {b.molecule!r} carries no real (non-empty GHS) sourced hazard -- "
                "routed AQUEOUS_NEUTRAL"
            )
    return WasteRequirement(frozenset(categories), tuple(sorted(set(reasons))))


def _procurement_catalysts_requirement(
    route: ExperimentRoute,
) -> "tuple[tuple[str, Availability | None], ...]":
    """One ``(name, tier)`` pair per catalyst ``route`` DECLARES (every step's ``ConditionEnvelope.catalysts``,
    deduplicated), ``tier`` resolved through the UNMODIFIED ``catalyst_availability`` classifier (``None`` =
    honest UNRECOGNIZED). Obtainability is profile-relative -- decided in :mod:`smartchem.capability.assess`."""
    seen: "dict[str, Availability | None]" = {}
    for step in route.steps:
        for cat in step.envelope.catalysts:
            if cat not in seen:
                seen[cat] = catalyst_availability(cat)
    return tuple(seen.items())


def compile_capability_requirements(route: ExperimentRoute) -> RouteCapabilityRequirements:
    """The PURE projection: what does ``route``'s own sourced evidence require, on every capability axis?

    Reads ONLY ``route`` -- never a :class:`~smartchem.capability.profile.CapabilityProfile`, never a
    named preset, never the network. Nothing here decides FIT/BLOCKED/UNKNOWN.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")

    equipment, equipment_unrecognized = _equipment_requirement(route)
    measurement, measurement_unrecognized = _measurement_requirement(route)
    procedure_forces, containment_reasons, hazard_unresolved = _procedure_hazard_scan(route)
    handling_care = verify_handling(route).care

    return RouteCapabilityRequirements(
        route_digest=route.digest,
        material=_material_requirements(route),
        equipment=equipment,
        equipment_unrecognized=equipment_unrecognized,
        physical=_physical_requirement(route),
        process=tuple(step.envelope.process for step in route.steps),
        containment=_containment_requirement(route, procedure_forces),
        containment_reasons=containment_reasons,
        hazard_unresolved=hazard_unresolved,
        measurement=measurement,
        measurement_unrecognized=measurement_unrecognized,
        waste=_waste_requirement(route),
        procurement_catalysts=_procurement_catalysts_requirement(route),
        attention_care=handling_care,
        monetary=basket_cost_vector(list(route.leaf_inputs)),
    )
