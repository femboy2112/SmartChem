"""Round V X-high D16 -- the D13 field-coverage theorem, machine-checked.

Three laws over :mod:`smartchem.capability.coverage`:

1. **Completeness** -- every dataclass field of every covered type has exactly one ledger row (a new field cannot be
   added silently; a removed field cannot leave a stale row).
2. **Axis witnesses** -- a PRESENT-but-untyped value on every axis-owned op/envelope slot leaves its OWNING axis UNKNOWN
   or BLOCKED, never FIT / NOT_APPLICABLE / UNCONSTRAINED, on a micro world where that axis is otherwise a pass.
3. **Noninterference witnesses** -- perturbing a PRESENTATION/READINESS-only field moves no capability axis at all
   (a mis-classified row -- a real demand filed as display -- would move one and fail here).
"""
from __future__ import annotations

import dataclasses as dc

import pytest

from smartchem.capability import compile_capability_requirements
from smartchem.capability.coverage import (
    AXIS_OWNERS,
    COVERED_TYPES,
    FIELD_COVERAGE,
    FieldCoverage,
    FieldOwner,
    missing_coverage,
    render_scale,
    render_summary,
    render_verification,
)
from smartchem.conditions import Interval

from tests.test_v0_9_round_v_xhigh_core import (
    PASSES,
    S,
    _assess,
    _op,
    _pf,
    _route,
)
from smartchem.procedure_evidence import OperationKind, OperationRole


def test_every_field_of_every_covered_type_has_exactly_one_ledger_row():
    assert missing_coverage() == ()
    assert len(COVERED_TYPES) == 10  # 0.9.5 S10: + StreamDisposition, StreamSubject
    assert all(type(v) is FieldCoverage and type(v.primary) is FieldOwner and v.law.strip()
               for v in FIELD_COVERAGE.values())


def test_the_completeness_check_is_discriminating():
    victim = ("ProcedureOperation", "rate")
    saved = FIELD_COVERAGE.pop(victim)
    try:
        assert "UNCOVERED ProcedureOperation.rate" in missing_coverage()
    finally:
        FIELD_COVERAGE[victim] = saved
    FIELD_COVERAGE[("ProcedureOperation", "no_such_field")] = saved
    try:
        assert "STALE ProcedureOperation.no_such_field" in missing_coverage()
    finally:
        del FIELD_COVERAGE[("ProcedureOperation", "no_such_field")]


def _axis(assessment, owner: FieldOwner):
    return getattr(assessment, owner.value.lower()).status


#: every axis-owned op slot a source can fill with PRESENT prose, with a hosting op on which that axis is otherwise
#: a pass in the clean micro world (the control asserts the pass).
_T = _pf(Interval(298.15, 298.15, "K"))
_OP_SLOTS = {
    "quantity": _op(OperationKind.FILTER, apparatus=("buchner funnel",)),
    "rate": _op(OperationKind.ADD),
    "agitation": _op(OperationKind.ADD),
    "temperature": _op(OperationKind.ADD),
    "pressure": _op(OperationKind.ADD),
    "duration": _op(OperationKind.ADD),
    "endpoint": _op(OperationKind.ADD, role=OperationRole.WASH),
}
_VERIFY = _op(OperationKind.VERIFY, apparatus=("analytical balance",))


@pytest.mark.parametrize("field", sorted(_OP_SLOTS))
def test_axis_witness_present_prose_on_an_op_slot_never_leaves_its_owner_a_pass(field):
    owner = FIELD_COVERAGE[("ProcedureOperation", field)].primary
    assert owner in AXIS_OWNERS
    host = _OP_SLOTS[field]
    control = _assess(_route(host, _VERIFY))
    assert _axis(control, owner) in PASSES, (field, owner, _axis(control, owner))
    witness = _assess(_route(dc.replace(host, **{field: _pf("a stated demand in prose")}), _VERIFY))
    assert _axis(witness, owner) in (S.UNKNOWN, S.BLOCKED), (field, owner)


@pytest.mark.parametrize("field, value, owner", [
    # ConditionEnvelope refuses a non-canonical unit at construction, so its typed slots are witnessed with a READ
    # demand the clean bench cannot meet (a 77 K stage, a 50 atm autoclave, a 3-week step over a 2-hour record):
    ("temperature", Interval(77, 77, "K"), FieldOwner.PHYSICAL),
    ("pressure", Interval(50, 50, "atm"), FieldOwner.PHYSICAL),
    ("duration", Interval(30240, 30240, "min"), FieldOwner.PROCESS),
    ("applied_field", "microwave irradiation", FieldOwner.EQUIPMENT),
    ("catalysts", ("zinc chloride",), FieldOwner.MATERIAL),
    # D24.3 (Wave-C' A5): an uncovered medium on a procedure step is an unread material question (never a species).
    ("medium", "benzene", FieldOwner.MATERIAL),
])
def test_axis_witness_envelope_slots_fail_closed_on_their_owner(field, value, owner):
    assert FIELD_COVERAGE[("ConditionEnvelope", field)].primary is owner
    assert _axis(_assess(_route()), owner) in PASSES
    assert _axis(_assess(_route(**{field: value})), owner) in (S.UNKNOWN, S.BLOCKED)


def _axes(assessment):
    return tuple((name, getattr(assessment, name).status) for name in (
        "material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
        "procurement", "attention_care", "monetary"))


def _with_op1(route, **changes):
    step = route.steps[0]
    proc = step.envelope.procedure
    op1 = dc.replace(proc.operations[0], **changes)
    proc = dc.replace(proc, operations=(op1,) + proc.operations[1:])
    return dc.replace(route, steps=(dc.replace(step, envelope=dc.replace(step.envelope, procedure=proc)),))


def _with_procedure(route, **changes):
    step = route.steps[0]
    proc = dc.replace(step.envelope.procedure, **changes)
    return dc.replace(route, steps=(dc.replace(step, envelope=dc.replace(step.envelope, procedure=proc)),))


def _with_use0(route, **changes):
    use = dc.replace(route.steps[0].envelope.procedure.operations[0].material_uses[0], **changes)
    uses = (use,) + route.steps[0].envelope.procedure.operations[0].material_uses[1:]
    return _with_op1(route, material_uses=uses)


@pytest.mark.parametrize("label, perturb", [
    ("ProcedureOperation.locator", lambda r: _with_op1(r, locator="a different source locator")),
    ("ProcedureEvidence.evidence_scope", lambda r: _with_procedure(r, evidence_scope="another scope note")),
    ("ProcedureEvidence.reaction_scope", lambda r: _with_procedure(r, reaction_scope="another reaction scope")),
    ("ProcedureMaterialUse.evidence_source", lambda r: _with_use0(r, evidence_source="another locator")),
    ("ConditionEnvelope.provenance", lambda r: _route(provenance="another conditions provenance note")),
])
def test_noninterference_witness_presentation_fields_move_no_axis(label, perturb):
    base = _route()
    owner_key = tuple(label.split("."))
    assert FIELD_COVERAGE[owner_key].primary in (FieldOwner.PRESENTATION_ONLY, FieldOwner.OUTSIDE_0_9_SCOPE)
    assert _axes(_assess(perturb(base))) == _axes(_assess(base)), label


def test_the_capability_core_never_reads_the_medium_as_a_species():
    """Part IV + D24.3: the medium text never becomes a species, a hazard entry or a re-quoted material string -- only a
    text-free unread note."""
    reqs = compile_capability_requirements(_route(medium="aqueous, acidic"))
    assert not any("aqueous, acidic" in text
                   for text in (*reqs.hazard_unresolved, *reqs.material_unresolved,
                                *(r.label for r in reqs.material)))
    assert any("envelope.medium" in u for u in reqs.material_unresolved)


# -- D24.1: the whole-procedure rows are witnessed through their CANONICAL renderings --------------------------------

_PROCEDURE_HOSTS = {
    "quench": _op(OperationKind.ADD, role=OperationRole.QUENCH),
    "workup_isolation": _op(OperationKind.ADD, role=OperationRole.WASH),
    "separation": _op(OperationKind.SEPARATE, apparatus=("separatory funnel",)),
    "wash": _op(OperationKind.ADD, role=OperationRole.WASH),
    "drying": _op(OperationKind.DRY, apparatus=("erlenmeyer flask",)),
    "purification": _op(OperationKind.DISTILL, apparatus=("simple distillation apparatus",), temperature=_T),
    "analytical_verification": _VERIFY,
    "scale": None,
}


@pytest.mark.parametrize("field", sorted(_PROCEDURE_HOSTS))
def test_axis_witness_a_procedure_row_is_display_only_when_canonical(field):
    """Every ProcedureEvidence row the ledger gives an AXIS owner (D24.1): its canonical rendering leaves the owner a
    pass; any other PRESENT prose leaves it UNKNOWN."""
    owner = FIELD_COVERAGE[("ProcedureEvidence", field)].primary
    assert owner in AXIS_OWNERS
    host = _PROCEDURE_HOSTS[field]
    base = _route(*(() if host is None else (host,)))
    proc = base.steps[0].envelope.procedure
    canonical = (render_scale(proc) if field == "scale" else
                 render_verification(proc) if field == "analytical_verification" else render_summary(proc, field))
    assert _axis(_assess(_with_procedure(base, **{field: _pf(canonical)})), owner) in PASSES, (field, canonical)
    assert _axis(_assess(_with_procedure(base, **{field: _pf("a stated demand in prose")})), owner) is S.UNKNOWN
