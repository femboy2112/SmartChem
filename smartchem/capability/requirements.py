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
from ..procedure_evidence import OperationKind, ProcedureMaterialRole
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
    #: Round IV F43: a TWO-SIDED composition band ``(low, high)`` on the stock's active fraction of this
    #: species -- the constraint a formulated wash needs (``required_assay`` is a one-sided FLOOR, right for a
    #: pure reagent but wrong for "5% NaHCO3 wash", which 100% bicarbonate would clear on a floor). Derived
    #: from the sourced FORMULATION vocabulary, never a fabricated number; ``None`` when the source states no
    #: formulation. A pure-reagent floor is expressed as the band ``(floor, 1.0)``.
    composition_band: "tuple[float, float] | None" = None

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
        if self.composition_band is not None:
            band = self.composition_band
            if (type(band) is not tuple or len(band) != 2
                    or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in band)
                    or not (0.0 <= float(band[0]) <= float(band[1]) <= 1.0)):
                raise ValueError(
                    "composition_band must be a (low, high) pair of fractions in [0, 1] with low<=high, or None"
                )
            object.__setattr__(self, "composition_band", (float(band[0]), float(band[1])))
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
    #: Round IV F48/F49: waste streams whose disposal ROUTING could not be positively determined -- an
    #: unassessed byproduct (never benign-by-negation) and every spent workup stream the source leaves without
    #: a disposal declaration. Surfaced, and in assess it caps the waste axis at UNKNOWN, never a silent pass.
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


#: Round IV F43/F45: the sourced compendial FORMULATION vocabulary -> a typed composition constraint on the
#: NAMED species plus its implied phase. Keyed on the formulation ADJECTIVE (generic across targets: any
#: "glacial" acid, any "5% aqueous" wash, any "anhydrous" drier), NEVER on a target identity -- the leaf
#: whitelist (_KNOWN_LEAF_IDS) and the runtime "glacial" prose scan are GONE (F45). A purity FLOOR is the
#: band ``(floor, 1.0)``; an unknown/absent formulation carries no composition gate (honest UNKNOWN). Each
#: band is source-scoped and defensible; the STOCK's own composition intervals live in data/material_library.py.
_FORMULATION_SPECS: "dict[str, tuple[tuple[float, float] | None, Phase | None, str]]" = {
    "glacial": ((0.99, 1.0), Phase.LIQUID,
                "USP/ACS 'glacial acetic acid' compendial formulation (>=99% mass fraction)"),
    "conc.": ((0.95, 1.0), Phase.LIQUID,
              "'concentrated' mineral acid formulation (>=95% mass fraction)"),
    "neat": (None, Phase.LIQUID,
             "a neat (undiluted) liquid reagent -- phase is the compatibility mechanism, no numeric floor"),
    "5% aqueous": ((0.045, 0.055), Phase.AQUEOUS_SOLUTION,
                   "a 5% w/w aqueous solution of the named solute (nominal 5% +-0.5% band)"),
    "saturated aqueous": ((0.20, 1.0), Phase.AQUEOUS_SOLUTION,
                          "a saturated aqueous solution -- the solute fraction must sit at/above the "
                          "saturation floor; an unsaturated dilute solution BLOCKS (F43)"),
    "anhydrous": ((0.97, 1.0), Phase.SOLID,
                  "the anhydrous form (>=97%); a hydrate carries bound water so its anhydrous fraction is "
                  "far lower and BLOCKS (F43)"),
}


def _formulation_spec(
    formulation: "str | None",
) -> "tuple[tuple[float, float] | None, Phase | None, str | None]":
    """Map a sourced formulation adjective to its typed ``(composition_band, phase, note)``. Normalizes case
    and interior whitespace ONLY -- never a fuzzy/substring prose scan (F45). An unrecognized or absent
    formulation carries no composition constraint and no implied phase -> honest UNKNOWN."""
    if formulation is None:
        return (None, None, None)
    key = " ".join(formulation.strip().casefold().split())
    spec = _FORMULATION_SPECS.get(key)
    if spec is None:
        return (None, None, None)
    return spec


def _sum_commensurable(quantities: "list[StockQuantity]") -> "StockQuantity | None":
    """F41: the whole-route demand for one (species, spec) group is the SUM of its per-op draws when they
    share a unit (25 mL twice -> 50 mL; 55 + 10 + 25 mL water -> 90 mL) -- never a first-value-wins
    truncation. Mixed or absent units cannot be summed without a conversion engine -> ``None`` (the assess
    side then treats the demand as an UNKNOWN quantity, never a silent pass)."""
    present = [q for q in quantities if q is not None]
    if not present:
        return None
    if len({q.unit for q in present}) != 1:
        return None
    total = sum(float(q.value) for q in present)
    return StockQuantity.of("%g" % total, present[0].unit)


def _material_requirements(route: ExperimentRoute) -> "tuple[MaterialRequirement, ...]":
    """Round IV F41/F43/F45/F50: ONE generic projection over every sourced ``ProcedureMaterialUse``. Reactants
    are now typed SUBSTRATE/REACTANT uses on the reaction op, so the leaf-identity whitelist and the runtime
    "glacial" prose scan are GONE (F45): the compiler reads reactant AND auxiliary semantics off the SAME
    ``material_uses`` without knowing the target. Uses of one species that share a semantic SPEC (identity or
    name + composition band + phase) are ONE requirement whose quantity is the SUM of their commensurable
    draws (F41); uses that DIFFER in spec stay SEPARATE (F50). The composition band + phase come from the
    sourced FORMULATION (F43). A leaf reactant the source never typed as a use still earns a bare identity
    requirement -- never silently dropped, never double-counted against a leaf a typed use already covers."""
    groups: "dict[tuple, dict]" = {}
    order: "list[tuple]" = []
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                band, formulation_phase, note = _formulation_spec(use.formulation)
                phase = use.phase if use.phase is not None else formulation_phase
                species_key = (("struct", _struct_digest(use.identity)) if use.identity is not None
                               else ("name", use.name.strip().casefold()))
                # F50: the SPEC is part of the key, so two uses of one species at different band/phase/
                # formulation are DISTINCT demands that never collapse; same spec -> one group, quantities
                # summed (F41), never a first-value-wins truncation.
                spec_key = (species_key, band, phase, (use.formulation or "").strip().casefold())
                group = groups.get(spec_key)
                if group is None:
                    group = {"identity": None, "names": set(), "roles": set(), "band": band, "phase": phase,
                             "quantities": [], "evidence": use.evidence_source, "note": note}
                    groups[spec_key] = group
                    order.append(spec_key)
                group["names"].add(use.name)
                group["roles"].add(use.role)
                if group["identity"] is None and use.identity is not None:
                    group["identity"] = use.identity
                if use.quantity is not None:
                    group["quantities"].append(use.quantity)
    projected_ids: "set[str]" = set()
    requirements: "list[MaterialRequirement]" = []
    for spec_key in order:
        group = groups[spec_key]
        name = min(group["names"], key=lambda n: (len(n.split()), len(n), n))
        roles = ", ".join(sorted(r.value for r in group["roles"]))
        if group["identity"] is not None:
            projected_ids.add(_struct_digest(group["identity"]))
        note = f" | formulation: {group['note']}" if group["note"] else ""
        # The composition band expresses the assay/formulation constraint (required_assay stays None -- a band
        # subsumes a floor). Phase + the SUMMED quantity participate exactly as the source declared them.
        requirements.append(MaterialRequirement(
            identity=group["identity"], required_assay=None, phase=group["phase"],
            quantity=_sum_commensurable(group["quantities"]),
            role=f"procedure material ({roles})",
            evidence_source=group["evidence"] + note, name=name, composition_band=group["band"],
        ))
    for leaf in route.leaf_inputs:
        if _struct_digest(leaf) not in projected_ids:
            requirements.append(MaterialRequirement(
                identity=leaf, required_assay=None, phase=None, quantity=None, role="reactant (leaf input)",
                evidence_source=(
                    "route leaf input (ExperimentRoute.leaf_inputs) with no typed source ProcedureMaterialUse "
                    "-- identity is required but no assay/phase/quantity/formulation is sourced, so those stay "
                    "UNKNOWN (never assumed)"),
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


#: Round IV F49: the workup material roles that become SPENT PROCESS STREAMS the bench must route as waste.
_SPENT_STREAM_ROLES = frozenset({
    ProcedureMaterialRole.WASH, ProcedureMaterialRole.RINSE, ProcedureMaterialRole.DRY,
    ProcedureMaterialRole.SOLVENT, ProcedureMaterialRole.NEUTRALIZE,
})


def _waste_requirement(route: ExperimentRoute) -> WasteRequirement:
    """Round IV F48/F49: waste-routing categories from the sourced byproduct ledger PLUS the workup spent
    streams. ``AQUEOUS_NEUTRAL`` is earned ONLY from POSITIVE evidence (an ASSESSED, empty-GHS byproduct) --
    an UNASSESSED byproduct is never benign-by-negation (F48) but an UNRESOLVED waste stream. Every spent
    workup stream (wash/rinse/drier/solvent/neutralize) the source leaves without a disposal declaration is
    also UNRESOLVED (F49): unknown composition does not need guessing to prove the obligation EXISTS. An
    off-gas needs ``OFFGAS_CAPTURE``; a real-GHS byproduct needs ``HAZARDOUS``. Unresolved streams cap the
    waste axis at UNKNOWN in assess -- never a silent pass."""
    handling = verify_handling(route)
    ghs_codes_by_name: "dict[str, tuple[str, ...]]" = {
        hazard.name: hazard.ghs_codes for step_handling in handling.steps for hazard in step_handling.hazards
    }
    categories: "set[WasteCapability]" = set()
    reasons: "list[str]" = []
    unresolved: "list[str]" = []
    for b in handling.all_byproducts:
        if b.hazard_name is None:
            # F48: an UNASSESSED byproduct is NOT aqueous/neutral by negation -- an unknown waste stream.
            unresolved.append(
                f"waste: balanced byproduct {b.molecule!r} has NO hazard assessment -- its disposal routing is "
                "UNKNOWN, never AQUEOUS_NEUTRAL by negation (F48)")
            continue
        is_real_hazard = bool(ghs_codes_by_name.get(b.hazard_name))
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
                f"waste: ASSESSED-benign condensed byproduct {b.molecule!r} ({b.hazard_name}, empty GHS) -- "
                "AQUEOUS_NEUTRAL from positive evidence, never by negation")
    seen: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                if use.role in _SPENT_STREAM_ROLES:
                    key = use.name.strip().casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    unresolved.append(
                        f"waste: spent workup stream {use.name!r} ({use.role.value}) -- the sourced procedure "
                        "declares no disposal routing, so its waste handling is UNKNOWN (F49, fail-closed)")
    return WasteRequirement(frozenset(categories), tuple(sorted(set(reasons))), tuple(sorted(set(unresolved))))


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
