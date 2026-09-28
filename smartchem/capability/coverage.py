"""smartchem/capability/coverage.py -- the D13 field-coverage theorem, MACHINE-CHECKED (Round V X-high, barrier D16).

**Listen, Morty. "Every stated demand reaches its axis or fails closed" is a THEOREM, and a theorem you only believe
because nobody added a field yet is a vibe.** Round V's D13 was proven by reading; the X-high pass then found PRESENT
``rate`` / ``agitation`` / ``endpoint`` / prose ``duration`` / prose ``temperature`` fields that reached NO axis at
all. So the ledger is now DATA: every field of every type a capability demand can live in is listed here with its ONE
owning axis (or an explicit non-capability role) and the fail-closed law a PRESENT-but-untyped value obeys.
:func:`missing_coverage` returns every dataclass field this table does not cover (and every stale entry) -- a test
pins it to ``()``, so a future field cannot be added silently: the day someone adds ``ProcedureOperation.stir_rate``
the suite goes red until a human decides which axis owns it.

Theorem boundary (stated, not hidden): every PRESENT prose field forces UNKNOWN on its OWN axis, so the fold
guarantees overall <= UNKNOWN; a demand MISFILED into another axis's prose field ("sit ~1 hour" typed into a
temperature slot) is caught on the HOST axis, not attributed to its owning one. Authored corpus data is re-filed by
hand and pinned by a curated corpus lint -- never by a runtime prose parser.

Pure data + one pure function; imports only the covered types. Nothing here decides a verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum

from ..conditions import ConditionEnvelope
from ..experiment.step import ExperimentRoute, ExperimentStep
from ..procedure_evidence import EvidenceField, ProcedureEvidence, ProcedureMaterialUse, ProcedureOperation
from ..process_constraints import ProcessRequirements

__all__ = [
    "FieldOwner",
    "FieldCoverage",
    "AXIS_OWNERS",
    "COVERED_TYPES",
    "FIELD_COVERAGE",
    "missing_coverage",
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
    ("ProcedureEvidence", "scale"): _c(_RD, "batch-level description; per-use typed quantities carry the material "
                                            "demand (corpus lint pins agreement)", _PS),
    ("ProcedureEvidence", "operations"): _c(_BOX, "each ProcedureOperation is covered field by field"),
    ("ProcedureEvidence", "quench"): _c(_RD, "presence/N_A gates readiness; realized by QUENCH-role ops"),
    ("ProcedureEvidence", "workup_isolation"): _c(_RD, "gates PROCESS_SPECIFIED; its ops are covered individually"),
    ("ProcedureEvidence", "separation"): _c(_RD, "realized by SEPARATE ops (coherence guard); the value is display"),
    ("ProcedureEvidence", "wash"): _c(_RD, "realized by WASH-role ops (coherence guard); the value is display"),
    ("ProcedureEvidence", "drying"): _c(_RD, "realized by DRY ops (coherence guard); the value is display"),
    ("ProcedureEvidence", "purification"): _c(_RD, "realized by DISTILL/RECRYSTALLIZATION ops; the value is display "
                                                   "(corpus lint pairs named techniques with ops)"),
    ("ProcedureEvidence", "analytical_verification"): _c(_ME, "PRESENT with no VERIFY op naming apparatus -> "
                                                              "measurement unread (UNKNOWN); methods ride on VERIFY ops"),
    ("ProcedureEvidence", "evidence_scope"): _c(_PS, "free-text scope note"),
    ("ProcedureEvidence", "unresolved_omissions"): _c(_RD, "blocks completeness (PROCESS_SPECIFIED); the HARD LAW is "
                                                           "the capability backstop"),
    # -- ProcedureOperation (one ordered op) ------------------------------------------------------------------------
    ("ProcedureOperation", "ordinal"): _c(_PS, "the total ORDER the D15 timeline composes over"),
    ("ProcedureOperation", "kind"): _c(_KEY, "routes the op to equipment (hardware kinds), measurement (VERIFY), "
                                             "physical (thermal kinds) and waste (spent-stream kinds)", _EQ, _W),
    ("ProcedureOperation", "role"): _c(_KEY, "routes the op to waste (WASH/RECRYSTALLIZATION) and readiness", _W),
    ("ProcedureOperation", "materials"): _c(_M, "each string no typed use of THIS op covers -> an untyped, "
                                                "unresolved requirement (D13) + an unresolved waste obligation (D17)",
                                            _W, _C),
    ("ProcedureOperation", "quantity"): _c(_M, "F69-analog: PRESENT with no quantified typed use on the op -> "
                                               "material_unresolved; otherwise the display form of the typed uses"),
    ("ProcedureOperation", "rate"): _c(_PR, "PRESENT -> process_unresolved (no rate-control coordinate exists)"),
    ("ProcedureOperation", "agitation"): _c(_PR, "PRESENT -> process_unresolved (no typed relation to the record's "
                                                 "Agitation mode)"),
    ("ProcedureOperation", "temperature"): _c(_PH, "typed K Interval -> the RANGE; prose -> physical_unresolved "
                                                   "(F-10: no same-step coverage); absent on a thermal op -> D14 ii/iii"),
    ("ProcedureOperation", "pressure"): _c(_PH, "typed atm Interval -> the window; prose -> physical_unresolved"),
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
    ("ProcedureMaterialUse", "formulation"): _c(_PS, "F69: non-empty with specification None -> unresolved term"),
    ("ProcedureMaterialUse", "phase"): _c(_M, "evidence-graded PhaseClaim (D18); ungraded evidence never decides"),
    ("ProcedureMaterialUse", "quantity"): _c(_M, "exact QuantityDemand; None -> an unstated (counted) use"),
    ("ProcedureMaterialUse", "evidence_source"): _c(_PS, "source locator"),
    ("ProcedureMaterialUse", "specification"): _c(_M, "THE comparison law (compare_specification)"),
    # -- EvidenceField (the tri-state slot) -------------------------------------------------------------------------
    ("EvidenceField", "status"): _c(_KEY, "PRESENT is the only status that states a demand"),
    ("EvidenceField", "value"): _c(_BOX, "owned by the PARENT field's owner (the row naming the slot)"),
    ("EvidenceField", "locator"): _c(_PS, "source locator"),
    ("EvidenceField", "justification"): _c(_RD, "closes out an EXPLICIT_NOT_APPLICABLE claim"),
    # -- ConditionEnvelope (the per-step conditions) ----------------------------------------------------------------
    ("ConditionEnvelope", "temperature"): _c(_PH, "typed Interval -> the RANGE; a non-K unit -> unread"),
    ("ConditionEnvelope", "pressure"): _c(_PH, "typed Interval -> the window; a non-atm unit -> unread"),
    ("ConditionEnvelope", "duration"): _c(_PR, "a timeline floor representation (MAX, never summed); non-min -> unread"),
    ("ConditionEnvelope", "medium"): _c(_PS, "condition prose, provenance ONLY (Part IV); a step with no "
                                             "ProcedureEvidence -> material_unresolved instead"),
    ("ConditionEnvelope", "catalysts"): _c(_M, "each string no CATALYST use covers -> untyped requirement; every "
                                               "declared catalyst -> procurement + a residual obligation", _PC, _W),
    ("ConditionEnvelope", "applied_field"): _c(_EQ, "PRESENT -> equipment unread (no mapping)"),
    ("ConditionEnvelope", "status"): _c(_RD, "conditions evidence strength (CONDITIONS_SUPPORTED)"),
    ("ConditionEnvelope", "provenance"): _c(_PS, "conditions provenance text"),
    ("ConditionEnvelope", "source"): _c(_RD, "conditions citation"),
    ("ConditionEnvelope", "process"): _c(_BOX, "the ProcessRequirements record, covered field by field"),
    ("ConditionEnvelope", "procedure"): _c(_BOX, "the ProcedureEvidence record; ABSENT -> material_unresolved + "
                                                 "physical D14 iv"),
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
