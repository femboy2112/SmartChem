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
* **A demand stated anywhere reaches its axis or that axis fails closed (D13, machine-checked by**
  :mod:`smartchem.capability.coverage` **since X-high D16).** Every raw ``op.materials`` string a typed use does not
  cover and every ``envelope.catalysts`` entry no CATALYST use covers become name-keyed, UNRESOLVED requirements
  (never FIT); a balanced species with no hazard record is carried as hazard-unresolved; the temperature RANGE,
  pressure window and the ordered procedure TIMELINE are read from every typed statement, and every stated-but-untyped
  demand (prose T/P/duration, a rate, an agitation, an endpoint, a thermal op nothing covers, a hardware op no
  admissible apparatus discharges, a VERIFY op naming no method, an amount with no typed home) is carried as an
  unread remainder on its OWNING axis (UNKNOWN). ``envelope.medium`` is condition prose -- never a species (Part IV),
  only a text-free unread note when no typed use covers it (D24.3).
* **Prose is display only when it IS the canonical rendering of the typed fields it summarizes (D24.1).** A PRESENT
  ``op.quantity`` / ``scale`` / whole-procedure summary / ``analytical_verification`` that is not byte-equal to its
  :mod:`smartchem.capability.coverage` renderer is unread on its named host axis -- no prose parser, no word list.
* **Waste is derived by** :func:`smartchem.capability.waste.derive_waste` **(D9)** -- this module only packages it.

Nothing here decides FIT/BLOCKED/UNKNOWN -- that fold lives in :mod:`smartchem.capability.assess`.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..category import Molecule
from ..constraints import PhysicalBounds
from ..contracts import Digestible, canonical_digest
from ..data.reagents import Availability
from ..experiment.affordability import CostVector, basket_cost_vector
from ..experiment.catalyst_availability import catalyst_availability
from ..experiment.equipment import EquipmentKind, equipment_for_step
from ..experiment.handling import CareLevel, verify_handling
from ..experiment.step import ExperimentRoute
from ..material_spec import MaterialSpecification, PhaseClaim
from ..procedure_evidence import OperationKind, ProcedureMaterialRole
from ..process_constraints import Agitation, ProcessRequirements
from .coverage import SUMMARY_FIELDS, render_op_quantity, render_scale, render_summary, render_verification
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
    * ``phase`` -- the use's own evidence-graded :class:`~smartchem.material_spec.PhaseClaim`, or ``None`` (never
      implied from words; D18: an ungraded phase can neither certify nor refute);
    * ``quantity`` -- the whole-route :class:`~.quantity.QuantityDemand`, NEVER ``None``;
    * ``untyped_source_text`` -- ``True`` when the only evidence is raw source text (an ``op.materials`` string, a
      catalyst or medium string no typed use covers): its ``name`` is that raw text, so ABSENCE under that key proves
      nothing (assess reads it as UNKNOWN, never BLOCKED) and its specification is unresolved (never FIT).
    """

    identity: "Molecule | None"
    phase: "PhaseClaim | None"
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
        if self.phase is not None and type(self.phase) is not PhaseClaim:
            raise TypeError("phase must be a smartchem.material_spec.PhaseClaim or None (D18: phase is evidence-graded)")
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
    projection could not read into the typed bounds (a non-canonical unit; prose; a thermal op no typed temperature
    or whole-step extremum covers; a timeline floor above the record's own ceiling; a stated rate/agitation) -> those
    axes fail closed to UNKNOWN. ``material_unresolved`` (X-high D16/D17 + D24) carries material demands that have no
    typed home (a step with no ``ProcedureEvidence`` at all; an op quantity or batch scale that is not the canonical
    rendering of its typed uses; an uncovered ``envelope.medium`` on a procedure step) -> the material axis fails
    closed to UNKNOWN (a provable BLOCK still wins).
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
    material_unresolved: "tuple[str, ...]" = ()

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
                     "measurement_unrecognized", "physical_unresolved", "process_unresolved",
                     "material_unresolved"):
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


@lru_cache(maxsize=1024)
def _resolved_name_digest(name: str) -> "str | None":
    """The canonical structure digest the OFFLINE NAME resolver assigns to ``name``, or ``None`` when the name does not
    resolve (unknown to the offline table, or not a name at all). Pure and deterministic -- no network."""
    from ..identity_parse import InputKind, resolve_target  # lazy: identity_parse is a heavier front-door module

    try:
        return _struct_digest(resolve_target(name, InputKind.NAME))
    except (ValueError, NotImplementedError):
        return None


def name_resolves_to(name: str, identity: Molecule) -> bool:
    """D25.1/D25.4 (Wave-C'' NEW-1, C6): does ``name`` resolve, through the offline NAME resolver, to the SAME canonical
    structure as ``identity``? A name the resolver does not know -- or one carrying extra words ("<species> + 2 g <a
    second species> in a sealed tube at 650 K", "cold <species>") -- is NOT a name of that identity."""
    digest = _resolved_name_digest(name.strip())
    return digest is not None and digest == _struct_digest(identity)


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
    UNRESOLVED term (UNKNOWN, never "no constraint"); otherwise the empty specification. D24.1 (Wave-C' A9): an EMPTY
    specification beside a non-empty formulation types NOTHING, so the words are just as untyped as with no
    specification at all -> the same unresolved term (a non-empty spec keeps D3's author-transcription contract)."""
    raw = (use.formulation or "").strip()
    spec = use.specification
    if spec is not None and not (raw and spec == _EMPTY_SPEC):
        return spec
    if raw:
        return MaterialSpecification(unresolved_terms=(raw,))
    return _EMPTY_SPEC


def _untyped_source_materials(route: ExperimentRoute) -> "list[tuple[str, str]]":
    """D13 P0-1/P0-2: every raw material string the source states that NO typed use covers, as ``(raw, locator)``:
    each ``op.materials`` entry not covered by a use OF THAT OP, and each ``envelope.catalysts`` entry not covered by
    a CATALYST use of that step. An op or step with no typed uses at all leaves every such string uncovered.

    X-high Part IV: ``envelope.medium`` is NOT read here any more. It is a CONDITION DESCRIPTION (the flagship record's
    medium is a whole sentence about dilution, catalysis, reflux and distillation), not a species -- turning the
    sentence into a name-keyed material, a hazard query and a spent stream overdetermined UNKNOWN for the wrong
    reason. Actual
    media/solvents are typed ``ProcedureMaterialUse`` s; a step with no ``ProcedureEvidence`` at all is carried as a
    text-free ``material_unresolved`` remainder instead (:func:`_material_unresolved`)."""
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
    return found


def _species_ident(molecule: Molecule) -> str:
    """The identity ``ExperimentStep`` itself keys stoichiometry on (resonance-canonical, shared with the search), so
    "produced by an earlier step" and "net-consumed by this step" read the SAME identity the balanced equation does."""
    from ..smiles import resonance_identity

    return resonance_identity(molecule)


def _role_contradiction(use, step) -> "str | None":
    """X-high F-7: a typed material ROLE must agree with the balanced reaction the use belongs to, wherever the
    structural model can perceive it (a known identity). A CATALYST the step NET-CONSUMES is a relabelled reactant (its
    leftover is a residual, not a regenerated catalyst); a SUBSTRATE/REACTANT the step does NOT net-consume is not a
    stoichiometric charge. Either contradiction is an UNRESOLVED role claim (UNKNOWN), never a confident reading --
    caught here, at requirement compilation, not in ``ExperimentStep`` (that would perturb search) and not as a raise
    (one bad source field must fail closed, not become a service error). Name-only uses are not judged."""
    if use.identity is None:
        return None
    consumed = step.net_consumes(use.identity)
    if use.role is ProcedureMaterialRole.CATALYST and consumed:
        return (f"role contradiction: {use.name!r} is typed CATALYST but its step's balanced reaction net-consumes it "
                "(a consumed reactant is not a regenerated catalyst)")
    if use.role in _STOICHIOMETRIC_ROLES and not consumed:
        return (f"role contradiction: {use.name!r} is typed {use.role.value} but its step's balanced reaction does not "
                "net-consume it")
    return None


def _external_inputs(route: ExperimentRoute) -> "list[tuple[int, object]]":
    """X-high S2 + D24.6: the route's EXTERNAL inputs IN STEP ORDER, as ``(step index, molecule)``. A reactant of step
    k is internal ONLY if it is step k-1's carried TARGET -- the one thing the linear route's own invariant says is
    handed forward. A byproduct of an earlier step (a condensation's small-molecule coproduct, removed in its workup) or a target
    consumed by any step other than its immediate successor is EXTERNAL: its later consumption is a real demand of its
    own (Wave-C' B2: one condensation byproduct fed two later hydrolyses for free). Recovery of a stream is a typed-disposition
    question (0.9.5 StreamDisposition), never assumed. One entry per (step, identity). ``ExperimentRoute.leaf_inputs``
    (order-blind, search/ranking contract) is deliberately left untouched."""
    out: "list[tuple[int, object]]" = []
    carried: "str | None" = None
    for s_index, step in enumerate(route.steps, start=1):
        seen: "set[str]" = set()
        for molecule in step.reactants:
            key = _species_ident(molecule)
            if key == carried or key in seen:
                continue
            seen.add(key)
            out.append((s_index, molecule))
        carried = _species_ident(step.target)
    return out


def _material_requirements(route: ExperimentRoute) -> "tuple[MaterialRequirement, ...]":
    """ONE generic projection over every sourced ``ProcedureMaterialUse`` (D1/D3). Uses group by (species key,
    projected-specification digest, declared phase claim): same group -> ONE requirement whose quantity is the exact
    :meth:`QuantityDemand.combine` of every use's quantity (an unquantified use is COUNTED, never dropped); different
    specification or phase -> separate requirements (the allocator in assess still spends each bottle once).
    X-high F-7: a use whose typed role contradicts its step's balanced reaction carries an unresolved role term.
    Then (D13) every uncovered raw material string becomes an untyped, unresolved, name-keyed requirement, and (X-high
    S1/S2) every EXTERNAL input a step consumes (in step order) that no stoichiometric typed use OF THAT STEP covers
    earns a bare structure requirement with an ``UNKNOWN`` quantity."""
    groups: "dict[tuple, dict]" = {}
    order: "list[tuple]" = []
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                spec = _project_specification(use)
                contradiction = _role_contradiction(use, step)
                if contradiction is not None:
                    spec = MaterialSpecification(composition=spec.composition, states=spec.states,
                                                 unresolved_terms=spec.unresolved_terms + (contradiction,))
                species_key = (("struct", _struct_digest(use.identity)) if use.identity is not None
                               else ("name", _norm_text(use.name)))
                phase_key = None if use.phase is None else canonical_digest(use.phase)
                key = (species_key, canonical_digest(spec), phase_key)
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
    requirements: "list[MaterialRequirement]" = []
    for key in order:
        group = groups[key]
        name = min(group["names"], key=lambda n: (len(n.split()), len(n), n))
        roles = ", ".join(sorted(r.value for r in group["roles"]))
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
    # X-high S1/S2: a consumed EXTERNAL input is charged PER STEP. Only a stoichiometric typed use (SUBSTRATE/REACTANT;
    # Wave-C nag: a wash never stands in) OF THE SAME STEP discharges that step's charge -- one step's typed 10 mL
    # never covers a later step's consumption of the same species. A species a step regenerates (both sides) must
    # still be POSSESSED to start, so any typed use of that step covers it; otherwise it is a bare demand too.
    leaves: "dict[str, dict]" = {}
    for s_index, molecule in _external_inputs(route):
        step = route.steps[s_index - 1]
        procedure = step.envelope.procedure
        key = _species_ident(molecule)
        step_uses = [] if procedure is None else [
            u for op in procedure.operations for u in op.material_uses
            if u.identity is not None and _species_ident(u.identity) == key]
        consumed = step.net_consumes(molecule)
        covering = [u for u in step_uses if u.role in _STOICHIOMETRIC_ROLES] if consumed else step_uses
        if covering:
            continue
        entry = leaves.setdefault(key, {"molecule": molecule, "steps": []})
        entry["steps"].append((s_index, consumed))
    for entry in leaves.values():
        where = ", ".join(f"step {i} ({'consumed' if c else 'regenerated'})" for i, c in entry["steps"])
        requirements.append(MaterialRequirement(
            identity=entry["molecule"], phase=None, quantity=QuantityDemand.unstated(len(entry["steps"])),
            role="reactant (leaf input)",
            evidence_source=(
                f"external route input at {where} (a reactant no EARLIER step produced) with no stoichiometric typed "
                "ProcedureMaterialUse of that step -- the identity is required (a real, positive demand), but no "
                "specification/phase/quantity is sourced, so those stay UNKNOWN (never assumed)"),
        ))
    return tuple(requirements)


def _is_canonical(field, rendering: str) -> bool:
    """D24.1: a PRESENT prose slot is DISPLAY only when its value is byte-equal to the canonical rendering of the typed
    fields it summarizes (an empty rendering never matches -- a slot with nothing typed behind it is unread)."""
    return bool(rendering) and isinstance(field.value, str) and field.value == rendering


def _material_unresolved(route: ExperimentRoute) -> "tuple[str, ...]":
    """X-high D16/D17 + D24 material remainders with no typed home (-> material UNKNOWN; a provable BLOCK still wins):

    * a step with NO ``ProcedureEvidence``: its auxiliary/medium/solvent material demand is unread;
    * D24.1 (Wave-C' A1/B3b): a PRESENT ``op.quantity`` that is not byte-equal to
      :func:`~smartchem.capability.coverage.render_op_quantity` (the op's quantified typed uses) -- the prose may state
      an amount or a material the typed uses do not ("5 L" beside a typed 20 mL use; "+ 2 g" of a second species);
    * D24.1: a PRESENT ``scale`` that is not byte-equal to :func:`~smartchem.capability.coverage.render_scale`;
    * D24.3 (Wave-C' A5/B3a): a non-empty ``envelope.medium`` on a step WITH ProcedureEvidence that no typed use of
      that step exact-fold-covers. The note is TEXT-FREE: the sentence is still never a species, a hazard entry or a
      waste stream (Part IV) -- it is only an open question about what material it might name;
    * D25.1 (Wave-C'' NEW-1): an identity-bearing typed use whose ``name`` is not a resolvable NAME of its own identity
      (offline NAME resolver, compared by canonical structure). The structure key carries the matching, so an
      unverified name is read by nothing -- and the canonical renderers build their text FROM it, so extra words in a
      name ("<species> + 2 g <a second species> in a sealed tube at 650 K") would otherwise ride through as "display".
      Such a name is an unread demand; "cold <species>" is one honestly ("cold" is a temperature demand in a name).
    """
    out: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is None:
            out.append(f"step {s_index} has no ProcedureEvidence: its auxiliary/medium material demand is unread "
                       "(no typed material uses to project)")
            continue
        unverified_names: "list[str]" = []
        for op in procedure.operations:
            for use in op.material_uses:
                if (use.identity is not None and use.name not in unverified_names
                        and not name_resolves_to(use.name, use.identity)):
                    unverified_names.append(use.name)
        for name in unverified_names:
            out.append(f"step {s_index} typed use name {name!r} is not a resolvable NAME of its own identity -- any "
                       "extra words it carries are an unread demand (D25.1)")
        for op in procedure.operations:
            field = op.quantity
            if field is None or not field.is_present:
                continue
            if not _is_canonical(field, render_op_quantity(op)):
                out.append(f"step {s_index} op {op.ordinal} {op.kind.value} states a quantity ({field.value!r}) that is "
                           "not the canonical rendering of its quantified typed uses -- a stated amount/material with "
                           "no typed home (D24.1)")
        if procedure.scale.is_present and not _is_canonical(procedure.scale, render_scale(procedure)):
            out.append(f"step {s_index} procedure scale ({procedure.scale.value!r}) is not the canonical rendering of its "
                       "quantified SUBSTRATE/REACTANT uses -- a stated batch amount with no typed home (D24.1)")
        medium = (step.envelope.medium or "").strip()
        step_uses = [u for op in procedure.operations for u in op.material_uses]
        if medium and not any(_name_covers(u.name, medium) for u in step_uses):
            out.append(f"step {s_index}: envelope.medium is untyped condition prose -- any material it names is unread "
                       "(D24.3; the sentence is never itself a species, hazard entry or waste stream)")
    return tuple(out)


#: D13 P0-4: op kinds that physically demand hardware. One of these naming NO apparatus is an unread equipment demand.
_HARDWARE_OP_KINDS = frozenset({
    OperationKind.HEAT, OperationKind.HOLD, OperationKind.COOL, OperationKind.DISTILL,
    OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY,
})

#: X-high F-4b: the CLOSED kind-admissibility table -- which recognized capabilities can physically discharge a
#: hardware op of each kind. A thermometer is real hardware but it does not distil anything. ``DRY`` has no entry: any
#: recognized non-consumable apparatus discharges it (a desiccator, an oven -- none is corpus-forced). Checked against
#: the corpus: every corpus hardware op with a recognized apparatus already carries a kind-appropriate one, so the table
#: adds no UNKNOWN to real data -- it only refuses the "wrong tool" laundering.
_KIND_ADMISSIBLE: "dict[OperationKind, frozenset[EquipmentCapability]]" = {
    OperationKind.HEAT: frozenset({EquipmentCapability.CONTROLLED_HEATING, EquipmentCapability.WATER_BATH}),
    OperationKind.HOLD: frozenset({EquipmentCapability.CONTROLLED_HEATING, EquipmentCapability.WATER_BATH,
                                   EquipmentCapability.REFLUX_CONDENSER, EquipmentCapability.ICE_BATH}),
    OperationKind.COOL: frozenset({EquipmentCapability.ICE_BATH}),
    OperationKind.DISTILL: frozenset({EquipmentCapability.SIMPLE_DISTILLATION,
                                      EquipmentCapability.FRACTIONAL_DISTILLATION}),
    OperationKind.SEPARATE: frozenset({EquipmentCapability.SEPARATORY_FUNNEL}),
    OperationKind.FILTER: frozenset({EquipmentCapability.GRAVITY_FILTRATION, EquipmentCapability.VACUUM_FILTRATION}),
}


def _equipment_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[EquipmentCapability], tuple[str, ...]]":
    """The union, over every step, of sourced apparatus strings classified through the closed resolver -- NEVER
    ``equipment_for_step`` (F1). VERIFY ops are SKIPPED (their apparatus is a measurement method). Vetted consumables
    are dropped; untabled apparatus is carried forward.

    X-high F-4/F-4b: the "hardware op names no apparatus" guard now runs AFTER resolution, PER OP: a hardware op must
    resolve at least one recognized NON-consumable capability admissible for its kind (``_KIND_ADMISSIBLE``). An
    ignored consumable ("boiling stones") never discharges a still, and a thermometer never discharges a DISTILL op.
    The step's ``ProcessRequirements.equipment`` adds demands but NEVER discharges an op (an unrelated record is not a
    typed op->record mapping). A declared applied field stays an unread demand, and (D24.17) so does the whole
    equipment demand of a step with no ``ProcedureEvidence``."""
    raw: "set[str]" = set()
    unread: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is None:
            # D24.17: no typed ops at all -- the step's equipment demand is unread, never NOT_APPLICABLE.
            unread.append(f"step {s_index} has no ProcedureEvidence: its equipment demand is unread (D24.17)")
        if procedure is not None:
            for op in procedure.operations:
                if op.kind is OperationKind.VERIFY:
                    continue
                raw.update(op.apparatus)
                if op.kind not in _HARDWARE_OP_KINDS:
                    continue
                where = f"step {s_index} op {op.ordinal} {op.kind.value}"
                recognized, ignored, unrecognized = classify_apparatus_strings(op.apparatus)
                if unrecognized:
                    continue  # the untabled string itself is carried forward as the open question
                if not recognized:
                    unread.append(f"{where} states no apparatus" if not ignored else
                                  f"{where} names only consumables ({', '.join(sorted(ignored))}) -- no "
                                  "non-consumable apparatus discharges its hardware demand (F-4)")
                    continue
                admissible = _KIND_ADMISSIBLE.get(op.kind)
                if admissible is not None and not (recognized & admissible):
                    unread.append(f"{where} names {', '.join(sorted(c.value for c in recognized))} but none of it can "
                                  f"perform a {op.kind.value} op (admissible: "
                                  f"{', '.join(sorted(c.value for c in admissible))}) (F-4b)")
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
    """The SPECIFIC :class:`MeasurementMethod` set the route's VERIFY ops demand, plus the untabled/unread remainder.

    X-high P5b: the guard is PER VERIFY OP, never pooled per step -- a second VERIFY op naming no method (a spot test
    with no instrument) is not discharged by the first op's balance. A procedure whose ``analytical_verification`` is
    PRESENT but whose VERIFY ops name nothing stays unread (D13). X-high D16: a PRESENT ``op.endpoint`` is an endpoint
    CRITERION ("until basic to litmus") with no typed carrier tying it to a method -> unread (no ``PH_INDICATOR`` is
    minted: a member no evidence path can emit would be decorative). D24.1: a PRESENT ``analytical_verification``
    that is not byte-equal to :func:`~smartchem.capability.coverage.render_verification` is unread (it may name a
    method no VERIFY op types). D24.17: a step with no ``ProcedureEvidence`` has an unread verification demand."""
    raw: "set[str]" = set()
    unread: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is None:
            # D24.17: no typed ops at all -- the step's verification demand is unread, never NOT_APPLICABLE.
            unread.append(f"step {s_index} has no ProcedureEvidence: its verification demand is unread (D24.17)")
            continue
        for op in procedure.operations:
            if op.endpoint is not None and op.endpoint.is_present:
                unread.append(f"step {s_index} op {op.ordinal} {op.kind.value} endpoint criterion "
                              f"{op.endpoint.value!r} is unread (no typed endpoint/measurement carrier)")
            if op.kind is not OperationKind.VERIFY:
                continue
            raw.update(op.apparatus)
            recognized, _ignored, unrecognized = classify_measurement_strings(op.apparatus)
            if not recognized and not unrecognized:
                unread.append(f"step {s_index} VERIFY op {op.ordinal} names no measurement apparatus -- its "
                              "verification demand is unread (P5b)")
        verification = procedure.analytical_verification
        if verification.is_present and not _is_canonical(verification, render_verification(procedure)):
            # D24.1 (Wave-C' A2): the stated verification text may demand a method no VERIFY op types ("1H NMR and
            # HPLC" beside a balance) -- it is display only when it IS the canonical rendering of the typed methods.
            unread.append(f"step {s_index} analytical verification ({verification.value!r}) is not the canonical "
                          "rendering of its VERIFY ops' typed methods -- an unread verification demand (D24.1)")
    recognized, _ignored, unrecognized = classify_measurement_strings(raw)
    return recognized, tuple(unrecognized) + tuple(sorted(set(unread)))


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


def _is_prose(field) -> bool:
    """A PRESENT field whose value is NOT a typed ``Interval`` -- a stated demand the compiler cannot read."""
    return field is not None and field.is_present and _interval_of(field) is None


#: X-high D14 (ii): op kinds whose HIGH temperature is implied (heating, holding at temperature, distilling).
_HIGH_THERMAL_KINDS = frozenset({OperationKind.HEAT, OperationKind.HOLD, OperationKind.DISTILL})
#: X-high D14 (iii): op kinds whose LOW temperature is implied (cooling; a hold can be cold too).
_LOW_THERMAL_KINDS = frozenset({OperationKind.COOL, OperationKind.HOLD})


def _physical_requirement(route: ExperimentRoute) -> "tuple[PhysicalBounds, tuple[str, ...]]":
    """X-high D14: the route's temperature is a RANGE and pressure a window, read from every TYPED statement:
    HIGH = max(process peak, envelope ``.hi``, op Interval ``.hi``); LOW = min(envelope ``.lo``, op Interval ``.lo``);
    pressure min/max likewise. Taking the extremum over STATED values is sound only when every thermal demand is
    stated, so the unread demands go to ``physical_unresolved`` (-> UNKNOWN, a provable BLOCK still wins):

    (i)  any PRESENT op temperature/pressure that is not a typed K/atm ``Interval`` -- prose ("650 C furnace") is
         never "covered" by an unrelated process extremum on the same step (F-10: no inferred relation);
    (ii) a HEAT/HOLD/DISTILL op with no typed temperature on a step whose process record carries no
         ``peak_temperature_k`` -- the record's own contract makes the peak the WHOLE-STEP extremum, the only
         legitimate cover (P4/P5: otherwise an unrelated lower statement masks it);
    (iii) a COOL/HOLD op with no typed temperature -- no whole-step MINIMUM exists to cover the low side (F-1);
    (iv) a step with no ``ProcedureEvidence``: its HIGH side is covered only by a process peak, its LOW side is unread;
    (v)  D24.1: a VACUUM_FILTRATION op with no typed pressure -- covered only by a sub-atmospheric whole-step record
         minimum (a record minimum >= 1 atm beside a vacuum op is contradictory).

    A non-canonical unit (not K / atm) is unread too (no unit engine)."""
    highs: "list[float]" = []
    lows: "list[float]" = []
    min_pressures: "list[float]" = []
    max_pressures: "list[float]" = []
    unresolved: "list[str]" = []

    def _temperature(interval, where: str) -> bool:
        if interval is None:
            return False
        if interval.unit != "K":
            unresolved.append(f"{where} temperature stated in {interval.unit!r}, not K -- unread (no unit engine)")
            return False
        highs.append(interval.hi)
        lows.append(interval.lo)
        return True

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
        has_peak = process is not None and process.peak_temperature_k is not None
        if process is not None:
            if process.peak_temperature_k is not None:
                highs.append(process.peak_temperature_k)
            if process.min_pressure_atm is not None:
                min_pressures.append(process.min_pressure_atm)
            if process.max_pressure_atm is not None:
                max_pressures.append(process.max_pressure_atm)
        _temperature(envelope.temperature, f"step {s_index} envelope")
        _pressure(envelope.pressure, f"step {s_index} envelope")
        procedure = envelope.procedure
        if procedure is None:
            if not has_peak:
                unresolved.append(f"step {s_index} has no ProcedureEvidence and no process peak temperature -- its "
                                  "HIGH temperature demand is unread (D14 iv)")
            unresolved.append(f"step {s_index} has no ProcedureEvidence -- its LOW temperature demand is unread "
                              "(no whole-step minimum exists; D14 iv)")
            continue
        for op in procedure.operations:
            where = f"step {s_index} op {op.ordinal} {op.kind.value}"
            for label, field in (("temperature", op.temperature), ("pressure", op.pressure)):
                if _is_prose(field):
                    unresolved.append(f"{where} states its {label} only in prose ({field.value!r}) -- an unread demand; "
                                      "a process extremum on the same step is not a typed relation to it (F-10)")
            typed = _temperature(_interval_of(op.temperature), where)
            _pressure(_interval_of(op.pressure), where)
            if (op.pressure is None or not op.pressure.is_present) and (
                    EquipmentCapability.VACUUM_FILTRATION in classify_apparatus_strings(op.apparatus)[0]):
                # D24.1 (Wave-C' A3): a vacuum op states a sub-atmospheric demand of unstated magnitude; only the step
                # record's whole-step MINIMUM can cover it, and a record minimum >= 1 atm contradicts the op itself
                # (vacuum means sub-atmospheric by definition -- not a tuned threshold).
                record_min = None if process is None else process.min_pressure_atm
                if record_min is None:
                    unresolved.append(f"{where} is a vacuum operation with no typed pressure, and step {s_index}'s "
                                      "process record carries no whole-step minimum pressure -- its LOW pressure "
                                      "demand is unread (D24.1)")
                elif record_min >= 1:
                    unresolved.append(f"{where} is a vacuum operation but step {s_index}'s process record claims a "
                                      f"whole-step minimum of {record_min:g} atm -- contradictory pressure evidence "
                                      "(D24.1)")
            if typed or _is_prose(op.temperature):
                continue  # a typed value is read; prose is already carried as unread (i)
            if op.kind in _HIGH_THERMAL_KINDS and not has_peak:
                unresolved.append(f"{where} demands heat but states no typed temperature and step {s_index}'s process "
                                  "record carries no whole-step peak -- its HIGH temperature demand is unread (D14 ii)")
            if op.kind in _LOW_THERMAL_KINDS:
                unresolved.append(f"{where} states no typed temperature -- its LOW temperature demand is unread (no "
                                  "whole-step minimum exists to cover it; D14 iii)")
    bounds = PhysicalBounds.of(
        max_temperature_k=max(highs) if highs else None,
        min_pressure_atm=min(min_pressures) if min_pressures else None,
        max_pressure_atm=max(max_pressures) if max_pressures else None,
        min_temperature_k=min(lows) if lows else None,
    )
    return bounds, tuple(unresolved)


def _step_timeline(s_index: int, step) -> "tuple[float | None, float | None, tuple[str, ...]]":
    """X-high D15: ONE step's procedure TIMELINE -> ``(floor_minutes, ceiling_minutes, unresolved)``.

    Ops are a TOTAL order (the evidence model cannot express concurrency, so none is invented): the typed-minute op
    durations ADD (``op_floor = sum(lo)``). Different REPRESENTATIONS of the same wall-clock (the op sum, the envelope
    duration, the record's ``min_elapsed_minutes`` / ``elapsed_minutes.lo``) are combined by MAX, never summed -- a
    process record that summarizes its ops must not double count them. Only the record's ``elapsed_minutes.hi`` is a
    CEILING (an op sum is never one: setup/transfer time is unowned). A floor above that ceiling is contradictory time
    evidence -> unresolved (UNKNOWN, never a guessed BLOCK). A PRESENT op duration that is not typed minutes is an
    unread demand (F-2)."""
    envelope = step.envelope
    record = envelope.process
    procedure = envelope.procedure
    unresolved: "list[str]" = []
    floors: "list[float]" = []
    op_floor = 0.0
    typed_ops = 0
    if procedure is not None:
        for op in procedure.operations:
            field = op.duration
            if field is None or not field.is_present:
                continue
            where = f"step {s_index} op {op.ordinal} {op.kind.value} duration"
            interval = _interval_of(field)
            if interval is None:
                unresolved.append(f"{where} {field.value!r} is stated in prose, not typed minutes -- an unread time "
                                  "demand (F-2)")
            elif interval.unit != "min":
                unresolved.append(f"{where} stated in {interval.unit!r}, not min -- unread (no unit engine)")
            else:
                op_floor += interval.lo
                typed_ops += 1
    if typed_ops:
        floors.append(op_floor)
    if envelope.duration is not None:
        if envelope.duration.unit != "min":
            unresolved.append(f"step {s_index} envelope duration stated in {envelope.duration.unit!r}, not min -- "
                              "unread (no unit engine)")
        else:
            floors.append(envelope.duration.lo)
    if record is not None:
        if record.min_elapsed_minutes is not None:
            floors.append(record.min_elapsed_minutes)
        if record.elapsed_minutes is not None:
            floors.append(record.elapsed_minutes.lo)
    floor = max(floors) if floors else None
    ceiling = None if record is None or record.elapsed_minutes is None else record.elapsed_minutes.hi
    if floor is not None and ceiling is not None and floor > ceiling:
        unresolved.append(f"step {s_index}: the stated timeline floor {floor:g} min exceeds the process record's own "
                          f"elapsed ceiling {ceiling:g} min -- contradictory time evidence, the process axis cannot "
                          "certify it (D15)")
    return floor, ceiling, tuple(unresolved)


def _effective_process(route: ExperimentRoute) -> "tuple[tuple[ProcessRequirements | None, ...], tuple[str, ...]]":
    """X-high D15: the per-step process records handed to the UNCHANGED 0.8 delegate, plus every stated time demand
    the projection could not read (``process_unresolved`` -- the ONE named field for "stated time demand not covered").

    A DECLARED record whose timeline floor exceeds its own known floor is handed on with ``min_elapsed_minutes`` raised
    to that floor (``dataclasses.replace``), so the delegate's existing floor exclusions see ordered ops (3 x 60 min
    against a 120-min bench is a provable BLOCK). ``None`` / undeclared records are passed through untouched -- the
    process axis's coverage gate reads them as the gap they are. A contradictory timeline is not handed on (UNKNOWN).
    X-high D16: a PRESENT ``op.rate`` (no rate-control coordinate exists) and a PRESENT ``op.agitation`` (no typed
    relation to the record's ``Agitation``) are unread process demands too; D24.4: a MIX op on a step whose record
    declares no agitation mode (or NONE); D24.1: a PRESENT whole-procedure summary that is not the canonical rendering
    of its realizing ops."""
    import dataclasses as dc

    records: "list[ProcessRequirements | None]" = []
    unresolved: "list[str]" = []
    for s_index, step in enumerate(route.steps, start=1):
        record = step.envelope.process
        floor, ceiling, notes = _step_timeline(s_index, step)
        unresolved.extend(notes)
        contradictory = floor is not None and ceiling is not None and floor > ceiling
        if (record is not None and record.is_declared and not contradictory and floor is not None and floor > 0):
            known = max((v for v in (record.min_elapsed_minutes,
                                     None if record.elapsed_minutes is None else record.elapsed_minutes.lo)
                         if v is not None), default=0.0)
            if floor > known:
                raised = max(floor, record.min_active_minutes or 0.0)
                record = dc.replace(record, min_elapsed_minutes=raised)
        records.append(record)
        procedure = step.envelope.procedure
        if procedure is not None:
            for name in SUMMARY_FIELDS:
                # D24.1 (Wave-C' A3): a PRESENT summary is what EARNS PROCESS_SPECIFIED, so it cannot hide behind the
                # HARD LAW -- its value is display only when it IS the canonical rendering of its realizing ops.
                field = getattr(procedure, name)
                if field.is_present and not _is_canonical(field, render_summary(procedure, name)):
                    unresolved.append(f"step {s_index} procedure {name} ({field.value!r}) is not the canonical "
                                      "rendering of its realizing ops -- an unread process demand (D24.1)")
            for op in procedure.operations:
                where = f"step {s_index} op {op.ordinal} {op.kind.value}"
                if op.kind is OperationKind.MIX:
                    # D24.4 (Wave-C' A6): a MIX op IS an agitation demand; a record that declares no agitation mode
                    # (or NONE) cannot carry it.
                    mode = None if record is None else record.agitation
                    if mode is None or mode is Agitation.NONE:
                        unresolved.append(f"{where} demands agitation but step {s_index}'s process record declares "
                                          f"{'no agitation mode' if mode is None else 'agitation NONE'} -- an unread "
                                          "(or contradictory) agitation demand (D24.4)")
                for label, field in (("rate", op.rate), ("agitation", op.agitation)):
                    if field is not None and field.is_present:
                        unresolved.append(f"{where} states an addition {label} ({field.value!r}) that no typed process "
                                          "coordinate carries -- an unread operator/process-control demand (D16)"
                                          if label == "rate" else
                                          f"{where} states an agitation demand ({field.value!r}) with no typed relation "
                                          "to the process record's agitation mode -- unread (D16)")
    return tuple(records), tuple(unresolved)


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
    process, process_unresolved = _effective_process(route)
    handling_care = verify_handling(route).care
    # X-high S2: the monetary basket prices the ORDER-AWARE external inputs (one of each distinct identity).
    basket: "list[Molecule]" = []
    basket_seen: "set[str]" = set()
    for _s_index, molecule in _external_inputs(route):
        key = _species_ident(molecule)
        if key not in basket_seen:
            basket_seen.add(key)
            basket.append(molecule)

    return RouteCapabilityRequirements(
        route_digest=route.digest,
        material=_material_requirements(route),
        equipment=equipment,
        equipment_unrecognized=equipment_unrecognized,
        physical=physical,
        process=process,
        containment=_containment_requirement(route, material_forces),
        containment_reasons=containment_reasons,
        hazard_unresolved=hazard_unresolved,
        measurement=measurement,
        measurement_unrecognized=measurement_unrecognized,
        waste=_waste_requirement(route),
        procurement_catalysts=_procurement_catalysts_requirement(route),
        attention_care=handling_care,
        monetary=basket_cost_vector(basket),
        physical_unresolved=physical_unresolved,
        process_unresolved=process_unresolved,
        material_unresolved=_material_unresolved(route),
    )
