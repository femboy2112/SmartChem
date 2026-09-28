"""v0.8 Round II -- procedure-evidence type well-formedness (Writer 1's one job).

These pin the STRUCTURAL contract only: EvidenceField tri-state coherence, ProcedureOperation shape, and
ProcedureEvidence well-formedness (contiguous ordinals, a reaction ADD, field<->operation coherence, is_sourced).
Completeness (readiness.procedure_representation_is_complete) and the readiness tier live in the readiness suite;
this file never asserts a tier.
"""
from __future__ import annotations

import pytest

from smartchem.conditions import Interval
from smartchem.procedure_evidence import (
    EvidenceField,
    EvidenceFieldStatus,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureOperation,
)
from smartchem.provenance import SourceCitation, SourceReview

_LOC = "https://chem.libretexts.org/example"
_SRC = SourceCitation(_LOC, SourceReview.ACCEPTED)


def _op(ordinal: int, kind: OperationKind, role: OperationRole = OperationRole.REACTION, **kw) -> ProcedureOperation:
    kw.setdefault("locator", _LOC)
    return ProcedureOperation(ordinal=ordinal, kind=kind, role=role, **kw)


def _complete_evidence(**overrides) -> ProcedureEvidence:
    """A fully-populated, sourced, coherent procedure (isopentyl-acetate-shaped)."""
    base = dict(
        reaction_scope="ester assembly: alcohol + acid -> ester + water",
        source=_SRC,
        scale=EvidenceField.present("0.020 mol alcohol; 1:1.5 acid excess", _LOC),
        operations=(
            _op(1, OperationKind.ADD, OperationRole.REACTION, materials=("isopentyl alcohol", "acetic acid"),
                rate=EvidenceField.present("combined, then acid slowly", _LOC),
                agitation=EvidenceField.present("swirl to mix", _LOC)),
            _op(2, OperationKind.HOLD, OperationRole.REACTION,
                temperature=EvidenceField.present(Interval(410.0, 420.0, "K"), _LOC),
                agitation=EvidenceField.present("gentle reflux", _LOC),
                duration=EvidenceField.present(Interval(60.0, 60.0, "min"), _LOC),
                endpoint=EvidenceField.present("reflux 1 hour", _LOC)),
            _op(3, OperationKind.SEPARATE, OperationRole.OTHER, materials=("aqueous layer",)),
            _op(4, OperationKind.DRY, OperationRole.OTHER, materials=("magnesium sulfate",)),
            _op(5, OperationKind.DISTILL, OperationRole.RECRYSTALLIZATION,
                endpoint=EvidenceField.present("collect 134-143 C fraction", _LOC)),
            _op(6, OperationKind.VERIFY, OperationRole.OTHER),
        ),
        quench=EvidenceField.not_applicable(_LOC, "no quench in the direct esterification workup"),
        workup_isolation=EvidenceField.present("extraction then dry", _LOC),
        separation=EvidenceField.present("separatory funnel extraction", _LOC),
        wash=EvidenceField.not_applicable(_LOC, "source describes extraction, no discrete wash step"),
        drying=EvidenceField.present("MgSO4", _LOC),
        purification=EvidenceField.present("fractional distillation", _LOC),
        analytical_verification=EvidenceField.present("boiling range of collected fraction", _LOC),
    )
    base.update(overrides)
    return ProcedureEvidence(**base)


def test_a_complete_sourced_procedure_builds_and_reports_its_source():
    ev = _complete_evidence()
    assert ev.is_sourced is True
    assert ev.source_locator == _LOC
    assert ev.digest  # digestible


def test_unsourced_or_unreviewed_evidence_is_not_sourced_and_has_no_source_locator():
    assert _complete_evidence(source=None).is_sourced is False
    assert _complete_evidence(source=None).source_locator is None
    unreviewed = SourceCitation(_LOC, SourceReview.UNREVIEWED)
    assert _complete_evidence(source=unreviewed).is_sourced is False


@pytest.mark.parametrize("bad", [
    dict(status=EvidenceFieldStatus.PRESENT, value="x", locator=None),          # PRESENT needs a locator
    dict(status=EvidenceFieldStatus.PRESENT, value=None, locator=_LOC),         # PRESENT needs a value
    dict(status=EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE, locator=_LOC),     # N/A needs a justification
    dict(status=EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE, justification="j"),  # N/A needs a locator
    dict(status=EvidenceFieldStatus.UNKNOWN_MISSING, value="x"),                # silence carries nothing
    dict(status=EvidenceFieldStatus.UNKNOWN_MISSING, locator=_LOC),
])
def test_evidence_field_status_value_locator_justification_coherence(bad):
    with pytest.raises((ValueError, TypeError)):
        EvidenceField(**bad)


def test_evidence_field_unknown_is_the_only_status_carrying_nothing():
    u = EvidenceField.unknown()
    assert u.is_unknown and u.value is None and u.locator is None and u.justification == ""


def test_procedure_operation_rejects_a_nonpositive_ordinal_or_missing_locator():
    with pytest.raises(ValueError):
        ProcedureOperation(ordinal=0, kind=OperationKind.ADD, locator=_LOC)
    with pytest.raises(ValueError):
        ProcedureOperation(ordinal=1, kind=OperationKind.ADD, locator="")


def test_procedure_rejects_noncontiguous_ordinals():
    with pytest.raises(ValueError):
        _complete_evidence(operations=(
            _op(1, OperationKind.ADD, OperationRole.REACTION),
            _op(3, OperationKind.VERIFY, OperationRole.OTHER),  # gap
        ))


def test_procedure_requires_a_reaction_add_operation():
    with pytest.raises(ValueError):
        _complete_evidence(operations=(
            _op(1, OperationKind.HEAT, OperationRole.OTHER),
            _op(2, OperationKind.VERIFY, OperationRole.OTHER),
        ))


def test_present_whole_field_needs_a_realizing_operation():
    # drying=PRESENT but no DRY operation among the ops -> refused
    with pytest.raises(ValueError):
        _complete_evidence(
            drying=EvidenceField.present("claimed drying", _LOC),
            operations=(
                _op(1, OperationKind.ADD, OperationRole.REACTION),
                _op(2, OperationKind.VERIFY, OperationRole.OTHER),
            ),
            # keep the other whole-fields consistent with a 2-op skeleton
            separation=EvidenceField.not_applicable(_LOC, "n/a"),
            wash=EvidenceField.not_applicable(_LOC, "n/a"),
            purification=EvidenceField.not_applicable(_LOC, "n/a"),
            workup_isolation=EvidenceField.not_applicable(_LOC, "n/a"),
        )


def test_explicit_not_applicable_field_forbids_a_realizing_operation():
    # wash=EXPLICIT_NOT_APPLICABLE while an ADD/role=WASH op exists -> refused (the M15 N/A-laundering guard)
    with pytest.raises(ValueError):
        _complete_evidence(
            wash=EvidenceField.not_applicable(_LOC, "claims no wash"),
            operations=(
                _op(1, OperationKind.ADD, OperationRole.REACTION),
                _op(2, OperationKind.ADD, OperationRole.WASH, materials=("water",)),
                _op(3, OperationKind.VERIFY, OperationRole.OTHER),
            ),
            separation=EvidenceField.not_applicable(_LOC, "n/a"),
            drying=EvidenceField.not_applicable(_LOC, "n/a"),
            purification=EvidenceField.not_applicable(_LOC, "n/a"),
            workup_isolation=EvidenceField.present("wash", _LOC),
        )


def test_digest_moves_when_a_field_status_changes():
    a = _complete_evidence()
    b = _complete_evidence(analytical_verification=EvidenceField.unknown())
    assert a.digest != b.digest
