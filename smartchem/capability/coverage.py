"""smartchem/capability/coverage.py -- the D13 field-coverage theorem, MACHINE-CHECKED (Round V X-high, barrier D16).

**Listen, Morty. "Every stated demand reaches its axis or fails closed" is a THEOREM, and a theorem you only believe
because nobody added a field yet is a vibe.** Round V's D13 was proven by reading; the X-high pass then found PRESENT
``rate`` / ``agitation`` / ``endpoint`` / prose ``duration`` / prose ``temperature`` fields that reached NO axis at
all. So the ledger is now DATA: every field of every type a capability demand can live in is listed here with its ONE
owning axis (or an explicit non-capability role) and the fail-closed law a PRESENT-but-untyped value obeys.
:func:`missing_coverage` returns every dataclass field this table does not cover (and every stale entry) -- a test
pins it to ``()``, so a future field cannot be added silently: the day someone adds ``ProcedureOperation.stir_rate``
the suite goes red until a human decides which axis owns it.

**D24.1 (post-Wave-C'): prose is DISPLAY only when it is byte-equal to the CANONICAL RENDERING of the typed fields it
summarizes; otherwise it is an unread demand on a NAMED host axis.** Wave C' killed the "typed field is authoritative,
prose is display" trust model in four places at once ("5 L methanol" beside a typed 20 mL use; "1H NMR and HPLC"
beside a balance; "vacuum distillation at 1 mmHg" as a purification summary; "anhydrous (<= 50 ppm H2O)" beside an
EMPTY specification). A word blacklist lint is foolable ("ice cold" walked straight through it). A canonical renderer is
not: the four ``render_*`` functions below are pure functions of the TYPED fields, and a PRESENT prose slot either IS
that rendering (so it can carry nothing the typed fields do not) or it is unread on the axis its row names. No prose
parser anywhere.

Theorem boundary (stated, not hidden): every PRESENT slot is either (a) read into its owning axis, (b) byte-equal to
the canonical rendering of the typed fields it summarizes, or (c) unread on its NAMED HOST axis (UNKNOWN), so the fold
guarantees overall <= UNKNOWN whenever a demand is not typed. A demand MISFILED into another axis's prose slot ("sit ~1
hour" typed into a temperature slot) is caught on the HOST axis, not attributed to its owning one. PRESENTATION-only
hosts (``evidence_scope``, an ``EvidenceField.justification``, locators, provenance text, claim notes) are OUTSIDE
the theorem: by contract they carry no capability demand, and a demand written there is not read by anything.

Pure data + pure functions; imports only the covered types and the closed measurement resolver. Nothing here decides a
verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum

from ..conditions import ConditionEnvelope
from ..experiment.step import ExperimentRoute, ExperimentStep
from ..procedure_evidence import (
    EvidenceField,
    OperationKind,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
    _field_matches,
)
from ..process_constraints import ProcessRequirements
from .measurement_resolver import classify_measurement_strings

__all__ = [
    "FieldOwner",
    "FieldCoverage",
    "AXIS_OWNERS",
    "COVERED_TYPES",
    "FIELD_COVERAGE",
    "SUMMARY_FIELDS",
    "missing_coverage",
    "render_op_quantity",
    "render_verification",
    "render_summary",
    "render_scale",
]


class FieldOwner(str, Enum):
    """Who answers for a field. The first nine are the capability AXES that can own a demand; the rest are explicit
    non-capability roles -- each a deliberate, reviewable ruling, never a default."""

    MATERIAL = "MATERIAL"
    PHYSICAL = "PHYSICAL"
    PROCESS = "PROCESS"
    EQUIPMENT = "EQUIPMENT"
    MEASUREMENT = "MEASUREMENT"
    WASTE = "WASTE"
    CONTAINMENT = "CONTAINMENT"
    PROCUREMENT = "PROCUREMENT"
    MONETARY = "MONETARY"
    READINESS_ONLY = "READINESS_ONLY"          # discharged by the 0.8 readiness ladder; the HARD LAW is the backstop
    PRESENTATION_ONLY = "PRESENTATION_ONLY"    # display/provenance; a typed field elsewhere is authoritative
    OUTSIDE_0_9_SCOPE = "OUTSIDE_0_9_SCOPE"    # a named 0.9.5+ item, never silently a pass
    CONTAINER = "CONTAINER"                    # holds other covered objects; its members are covered individually
    ROUTING_KEY = "ROUTING_KEY"                # a closed discriminator the owning axes switch on (kind, role, status)


#: the owners that are capability AXES (a PRESENT-but-untyped value on a field they own must leave that axis
#: UNKNOWN or BLOCKED -- never FIT, NOT_APPLICABLE or UNCONSTRAINED).
AXIS_OWNERS: "frozenset[FieldOwner]" = frozenset({
    FieldOwner.MATERIAL, FieldOwner.PHYSICAL, FieldOwner.PROCESS, FieldOwner.EQUIPMENT, FieldOwner.MEASUREMENT,
    FieldOwner.WASTE, FieldOwner.CONTAINMENT, FieldOwner.PROCUREMENT, FieldOwner.MONETARY,
})


@dataclass(frozen=True)
class FieldCoverage:
    """One ledger row: the PRIMARY owner, any secondary readers, and the law a PRESENT untyped value obeys."""

    primary: FieldOwner
    law: str
    also: "tuple[FieldOwner, ...]" = ()


#: every type a capability demand can be stated in (the D13 surface).
COVERED_TYPES: "tuple[type, ...]" = (
    ProcedureEvidence, ProcedureOperation, ProcedureMaterialUse, EvidenceField,
    ConditionEnvelope, ProcessRequirements, ExperimentStep, ExperimentRoute,
)

_M, _PH, _PR, _EQ, _ME, _W = (FieldOwner.MATERIAL, FieldOwner.PHYSICAL, FieldOwner.PROCESS, FieldOwner.EQUIPMENT,
                              FieldOwner.MEASUREMENT, FieldOwner.WASTE)
_C, _PC, _MO = FieldOwner.CONTAINMENT, FieldOwner.PROCUREMENT, FieldOwner.MONETARY
_RD, _PS, _OUT = FieldOwner.READINESS_ONLY, FieldOwner.PRESENTATION_ONLY, FieldOwner.OUTSIDE_0_9_SCOPE
_BOX, _KEY = FieldOwner.CONTAINER, FieldOwner.ROUTING_KEY


def _c(primary: FieldOwner, law: str, *also: FieldOwner) -> FieldCoverage:
    return FieldCoverage(primary, law, tuple(also))


#: THE LEDGER. Keyed by (type name, field name). Every row is a ruling a reviewer can dispute line by line.
FIELD_COVERAGE: "dict[tuple[str, str], FieldCoverage]" = {
    # -- ProcedureEvidence (the whole-procedure record) ------------------------------------------------------------
    ("ProcedureEvidence", "reaction_scope"): _c(_OUT, "source-subject binding is a 0.9.5 item; not a capability demand"),
    ("ProcedureEvidence", "source"): _c(_RD, "sourcing gates PROCESS_SPECIFIED; below it the HARD LAW caps FIT"),
    ("ProcedureEvidence", "scale"): _c(_M, "D24.1: PRESENT and not byte-equal to render_scale() (the quantified "
                                           "SUBSTRATE/REACTANT uses) -> material_unresolved", _RD),
    ("ProcedureEvidence", "operations"): _c(_BOX, "each ProcedureOperation is covered field by field"),
    # D24.1 (Wave-C' A3): a PRESENT summary is what EARNS PROCESS_SPECIFIED, so the HARD LAW is NOT its backstop --
    # its value must be the canonical rendering of its realizing ops, or it is unread on the PROCESS host axis.
    ("ProcedureEvidence", "quench"): _c(_PR, "D24.1: PRESENT and not byte-equal to render_summary(p, 'quench') -> "
                                             "process_unresolved; presence/N_A also gates readiness", _RD),
    ("ProcedureEvidence", "workup_isolation"): _c(_PR, "D24.1: PRESENT and not render_summary(...) -> "
                                                       "process_unresolved; gates PROCESS_SPECIFIED", _RD),
    ("ProcedureEvidence", "separation"): _c(_PR, "D24.1: PRESENT and not render_summary(...) -> process_unresolved",
                                            _RD),
    ("ProcedureEvidence", "wash"): _c(_PR, "D24.1: PRESENT and not render_summary(...) -> process_unresolved", _RD),
    ("ProcedureEvidence", "drying"): _c(_PR, "D24.1: PRESENT and not render_summary(...) -> process_unresolved", _RD),
    ("ProcedureEvidence", "purification"): _c(_PR, "D24.1: PRESENT and not render_summary(...) -> "
                                                   "process_unresolved", _RD),
    ("ProcedureEvidence", "analytical_verification"): _c(_ME, "D24.1: PRESENT and not byte-equal to "
                                                              "render_verification() (the VERIFY ops' typed methods) "
                                                              "-> measurement_unrecognized"),
    ("ProcedureEvidence", "evidence_scope"): _c(_PS, "free-text scope note"),
    ("ProcedureEvidence", "unresolved_omissions"): _c(_RD, "blocks completeness (PROCESS_SPECIFIED); the HARD LAW is "
                                                           "the capability backstop"),
    # -- ProcedureOperation (one ordered op) ------------------------------------------------------------------------
    ("ProcedureOperation", "ordinal"): _c(_PS, "the total ORDER the D15 timeline composes over"),
    ("ProcedureOperation", "kind"): _c(_KEY, "routes the op to equipment (hardware kinds), measurement (VERIFY), "
                                             "physical (thermal kinds), process (MIX: D24.4 -- a MIX op on a step "
                                             "whose record agitation is None/NONE -> process_unresolved) and waste "
                                             "(spent-stream kinds)", _EQ, _PR, _W),
    ("ProcedureOperation", "role"): _c(_KEY, "routes the op to waste (WASH/RECRYSTALLIZATION) and readiness", _W),
    ("ProcedureOperation", "materials"): _c(_M, "each string no typed use of THIS op covers -> an untyped, "
                                                "unresolved requirement (D13) + an unresolved waste obligation (D17)",
                                            _W, _C),
    ("ProcedureOperation", "quantity"): _c(_M, "D24.1: PRESENT and not byte-equal to render_op_quantity(op) (the "
                                               "op's quantified typed uses) -> material_unresolved"),
    ("ProcedureOperation", "rate"): _c(_PR, "PRESENT -> process_unresolved (no rate-control coordinate exists)"),
    ("ProcedureOperation", "agitation"): _c(_PR, "PRESENT -> process_unresolved (no typed relation to the record's "
                                                 "Agitation mode)"),
    ("ProcedureOperation", "temperature"): _c(_PH, "typed K Interval -> the RANGE; prose -> physical_unresolved "
                                                   "(F-10: no same-step coverage); absent on a thermal op -> D14 ii/iii"),
    ("ProcedureOperation", "pressure"): _c(_PH, "typed atm Interval -> the window; prose -> physical_unresolved; "
                                               "D24.1: a VACUUM_FILTRATION op with no typed pressure needs the step "
                                               "record's sub-atmospheric minimum (a record >= 1 atm is contradictory)"),
    ("ProcedureOperation", "duration"): _c(_PR, "typed min Interval -> the ordered TIMELINE floor; prose -> "
                                                "process_unresolved (F-2)"),
    ("ProcedureOperation", "endpoint"): _c(_ME, "PRESENT -> measurement_unrecognized (no typed endpoint carrier)"),
    ("ProcedureOperation", "apparatus"): _c(_EQ, "per-op post-resolution guard: a hardware op needs >= 1 recognized "
                                                 "non-consumable ADMISSIBLE capability (F-4/F-4b); untabled -> UNKNOWN; "
                                                 "on VERIFY ops -> measurement (per-op, P5b)", _ME),
    ("ProcedureOperation", "material_uses"): _c(_M, "typed uses: projected + allocated (D1/D2); roles checked against "
                                                    "the step's net consumption (F-7)", _W, _C, _PC),
    ("ProcedureOperation", "locator"): _c(_PS, "source locator"),
    # -- ProcedureMaterialUse (one typed material use) --------------------------------------------------------------
    ("ProcedureMaterialUse", "name"): _c(_M, "name key when identity is None; hazard lookup; waste naming", _C, _W),
    ("ProcedureMaterialUse", "role"): _c(_M, "stoichiometric roles discharge a leaf; CATALYST -> procurement; role "
                                             "contradicting net consumption -> unresolved (F-7)", _W, _PC),
    ("ProcedureMaterialUse", "identity"): _c(_M, "structure key; hazard; residual/cover keys", _C, _W),
    ("ProcedureMaterialUse", "formulation"): _c(_PS, "F69 (+ D24.1 A9): non-empty with specification None OR an "
                                                     "EMPTY specification -> unresolved term; a non-empty spec keeps "
                                                     "the D3 author-transcription contract"),
    ("ProcedureMaterialUse", "phase"): _c(_M, "evidence-graded PhaseClaim (D18); ungraded evidence never decides"),
    ("ProcedureMaterialUse", "quantity"): _c(_M, "exact QuantityDemand; None -> an unstated (counted) use"),
    ("ProcedureMaterialUse", "evidence_source"): _c(_PS, "source locator"),
    ("ProcedureMaterialUse", "specification"): _c(_M, "THE comparison law (compare_specification)"),
    # -- EvidenceField (the tri-state slot) -------------------------------------------------------------------------
    ("EvidenceField", "status"): _c(_KEY, "PRESENT is the only status that states a demand (D24.2: an "
                                          "EXPLICIT_NOT_APPLICABLE field carries no value)"),
    ("EvidenceField", "value"): _c(_BOX, "owned by the PARENT field's owner (the row naming the slot)"),
    ("EvidenceField", "locator"): _c(_PS, "source locator"),
    ("EvidenceField", "justification"): _c(_RD, "closes out an EXPLICIT_NOT_APPLICABLE claim; a PRESENTATION host "
                                                 "OUTSIDE the D13 theorem (a demand written here is not read)"),
    # -- ConditionEnvelope (the per-step conditions) ----------------------------------------------------------------
    ("ConditionEnvelope", "temperature"): _c(_PH, "typed Interval -> the RANGE; a non-K unit -> unread"),
    ("ConditionEnvelope", "pressure"): _c(_PH, "typed Interval -> the window; a non-atm unit -> unread"),
    ("ConditionEnvelope", "duration"): _c(_PR, "a timeline floor representation (MAX, never summed); non-min -> unread"),
    ("ConditionEnvelope", "medium"): _c(_M, "condition prose, never a species/hazard/waste stream (Part IV); D24.3: "
                                            "non-empty and not exact-fold-covered by a typed use of that step -> a "
                                            "text-free material_unresolved note (a step with no ProcedureEvidence "
                                            "-> material_unresolved anyway)", _PS),
    ("ConditionEnvelope", "catalysts"): _c(_M, "each string no CATALYST use covers -> untyped requirement; every "
                                               "declared catalyst -> procurement + a residual obligation", _PC, _W),
    ("ConditionEnvelope", "applied_field"): _c(_EQ, "PRESENT -> equipment unread (no mapping)"),
    ("ConditionEnvelope", "status"): _c(_RD, "conditions evidence strength (CONDITIONS_SUPPORTED)"),
    ("ConditionEnvelope", "provenance"): _c(_PS, "conditions provenance text"),
    ("ConditionEnvelope", "source"): _c(_RD, "conditions citation"),
    ("ConditionEnvelope", "process"): _c(_BOX, "the ProcessRequirements record, covered field by field"),
    ("ConditionEnvelope", "procedure"): _c(_BOX, "the ProcedureEvidence record; ABSENT -> material_unresolved + "
                                                 "physical D14 iv + equipment/measurement unread (D24.17)"),
    # -- ProcessRequirements (the 0.8 whole-step record) ------------------------------------------------------------
    ("ProcessRequirements", "elapsed_minutes"): _c(_PR, "the ONLY step ceiling; .lo is a timeline floor"),
    ("ProcessRequirements", "active_minutes"): _c(_PR, "compared by the delegate against max_active_minutes"),
    ("ProcessRequirements", "attention"): _c(_PR, "compared against allowed_attention (never NO_LIMIT)"),
    ("ProcessRequirements", "check_interval_minutes"): _c(_PR, "compared against min_check_interval_minutes"),
    ("ProcessRequirements", "agitation"): _c(_PR, "compared against allowed_agitation (never NO_LIMIT)"),
    ("ProcessRequirements", "equipment"): _c(_EQ, "adds recognized demands; NEVER discharges an op (F-4)"),
    ("ProcessRequirements", "workup_included"): _c(_PR, "False -> the coverage gate: UNKNOWN (D15)"),
    ("ProcessRequirements", "provenance"): _c(_PS, "process provenance text"),
    ("ProcessRequirements", "source"): _c(_RD, "process citation (PROCESS_SPECIFIED)"),
    ("ProcessRequirements", "peak_temperature_k"): _c(_PH, "the WHOLE-STEP high extremum (the only cover for a "
                                                           "thermal op's unstated high side)"),
    ("ProcessRequirements", "min_pressure_atm"): _c(_PH, "the whole-step low pressure extremum"),
    ("ProcessRequirements", "max_pressure_atm"): _c(_PH, "the whole-step high pressure extremum"),
    ("ProcessRequirements", "min_elapsed_minutes"): _c(_PR, "a timeline floor representation (MAX); the delegate "
                                                            "EXCLUDES a known floor above a bound"),
    ("ProcessRequirements", "min_active_minutes"): _c(_PR, "a known active floor (EXCLUDES above the bound)"),
    # -- ExperimentStep / ExperimentRoute ---------------------------------------------------------------------------
    ("ExperimentStep", "schema_version"): _c(_KEY, "shape identity"),
    ("ExperimentStep", "target"): _c(_PS, "the step's product identity (search), not a capability demand"),
    ("ExperimentStep", "reactants"): _c(_M, "external inputs IN STEP ORDER (S1/S2) -> leaf demands; hazard scan; "
                                            "residuals; monetary basket", _W, _C, _MO),
    ("ExperimentStep", "products"): _c(_C, "hazard scan; byproduct waste via handling; 'produced earlier' key", _W),
    ("ExperimentStep", "reagents"): _c(_W, "a subset of reactants (material coverage inherited); residuals"),
    ("ExperimentStep", "envelope"): _c(_BOX, "the ConditionEnvelope, covered field by field"),
    ("ExperimentStep", "reaction_center"): _c(_OUT, "mechanistic locus; not a capability demand"),
    ("ExperimentRoute", "schema_version"): _c(_KEY, "shape identity"),
    ("ExperimentRoute", "steps"): _c(_BOX, "each ExperimentStep, in ORDER"),
}


#: the whole-procedure SUMMARY fields rendered by :func:`render_summary` (their host axis is PROCESS -- D24.1).
SUMMARY_FIELDS: "tuple[str, ...]" = ("quench", "workup_isolation", "separation", "wash", "drying", "purification")


def _render_use(use: ProcedureMaterialUse) -> str:
    return f"{use.quantity.value} {use.quantity.unit} {use.name}"


def render_op_quantity(op: ProcedureOperation) -> str:
    """D24.1: the CANONICAL rendering of an op's typed amounts -- its QUANTIFIED typed uses, in use order,
    ``"<value> <unit> <name>"`` joined by ``" + "`` (``""`` when none). A PRESENT ``op.quantity`` is display only if it
    is byte-equal to this string."""
    return " + ".join(_render_use(u) for u in op.material_uses if u.quantity is not None)


def render_verification(procedure: ProcedureEvidence) -> str:
    """D24.1: the CANONICAL rendering of a procedure's typed verification -- the sorted resolved
    :class:`~smartchem.capability.enums.MeasurementMethod` values of its VERIFY ops joined by ``"; "``."""
    methods: "set[str]" = set()
    for op in procedure.operations:
        if op.kind is OperationKind.VERIFY:
            recognized, _ignored, _unrecognized = classify_measurement_strings(op.apparatus)
            methods.update(m.value for m in recognized)
    return "; ".join(sorted(methods))


def render_summary(procedure: ProcedureEvidence, field: str) -> str:
    """D24.1: the CANONICAL rendering of a whole-procedure summary field -- its realizing ops (the SAME kind/role
    bookkeeping the 0.8 coherence guard uses) as ``"op <n> <KIND>/<ROLE>"`` joined by ``"; "``."""
    if field not in SUMMARY_FIELDS:
        raise ValueError(f"{field!r} is not a whole-procedure summary field; known: {SUMMARY_FIELDS}")
    return "; ".join(f"op {op.ordinal} {op.kind.value}/{op.role.value}" for op in procedure.operations
                     if _field_matches(procedure, field, op))


def render_scale(procedure: ProcedureEvidence) -> str:
    """D24.1: the CANONICAL rendering of a procedure's batch scale -- its quantified SUBSTRATE/REACTANT uses, in op
    order, ``"<value> <unit> <name>"`` joined by ``" + "``."""
    stoich = (ProcedureMaterialRole.SUBSTRATE, ProcedureMaterialRole.REACTANT)
    return " + ".join(_render_use(u) for op in procedure.operations for u in op.material_uses
                      if u.role in stoich and u.quantity is not None)


def missing_coverage() -> "tuple[str, ...]":
    """Every ``Type.field`` present in a covered dataclass but absent from :data:`FIELD_COVERAGE`, and every table
    entry naming a field that no longer exists. ``()`` is the theorem's structural half; a test pins it."""
    problems: "list[str]" = []
    present: "set[tuple[str, str]]" = set()
    for cls in COVERED_TYPES:
        for f in fields(cls):
            key = (cls.__name__, f.name)
            present.add(key)
            if key not in FIELD_COVERAGE:
                problems.append(f"UNCOVERED {cls.__name__}.{f.name}")
    for key in FIELD_COVERAGE:
        if key not in present:
            problems.append(f"STALE {key[0]}.{key[1]}")
    return tuple(sorted(problems))
