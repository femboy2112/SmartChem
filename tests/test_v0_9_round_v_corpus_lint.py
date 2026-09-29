"""v0.9 Round V X-high -- the authored-corpus LINT (barrier D14 data, D16 re-filing, D17 medium review, D18 phase).

**Existence is pain, Jerry, and so is a demand filed in the wrong drawer.** The D13 field-coverage theorem makes every
PRESENT prose field fail closed on its OWN axis -- but it cannot attribute a demand the author MISFILED into another
axis's prose (a time hidden in a temperature slot fails closed on PHYSICAL, while PROCESS never hears of it). That is
not a runtime job: nothing in the compiler may parse prose. It is an AUTHORING discipline, and this file is its guard:
curated, data-only checks over the hand-authored corpus in ``smartchem/decompiler_conditions.py``. A future author who
files "swirl for 10 minutes" into ``quantity`` fails here, loudly, before any axis can be fooled.

What is pinned:

* D18 -- every corpus use's phase is an evidence-graded ``PhaseClaim`` (never a bare ``Phase``); SOURCE_QUOTED only
  with a ``page:`` quote in its note; the stale Round-V "author inference" reading of the isopentyl bicarbonate
  phase is corrected (the cited page says "5% aqueous sodium bicarbonate").
* D16 filing -- no time words in temperature/quantity/endpoint slots unless the same op carries a TYPED duration;
  no bath/agitation/vacuum words in quantity slots; paracetamol's "4-8 minutes" is a typed Interval.
* D16 pairing -- every verification method the record's text names is carried by a VERIFY op and every VERIFY op
  carries a named method (the aspirin ferric-chloride test was text-only -- P5b); every whole-procedure summary
  technique is realized by a concrete op.
* D17 (Part IV) -- every corpus ``envelope.medium`` string is condition prose whose material words are each typed
  elsewhere (or honestly absent); the compiler never reads the sentence as a species.
* D14 data -- the isopentyl whole-step peak and the aspirin whole-step minimum pressure are UNKNOWN (P-X2/P-X3), and
  the re-filing leaves every procedure's completeness (hence every readiness tier) untouched.
* D24.1 -- exactly the curated ops' ``quantity`` is AUTHORED as the canonical rendering of their typed uses (the
  compiler reads everything else as an unread material demand); no corpus ``scale`` is forced into equality.
* D24.16 -- no authored text claims FRACTIONAL distillation (the page describes a 134-143 C cut).
"""
from __future__ import annotations

import re

import pytest

from smartchem.conditions import Interval
from smartchem.decompiler_conditions import (
    _ASPIRIN_PROCEDURE,
    _ISOPENTYL_PROCEDURE,
    _PARACETAMOL_PROCEDURE,
    SEED_CONDITIONS,
)
from smartchem.experiment.readiness import procedure_representation_is_complete
from smartchem.experiment.stock import Phase
from smartchem.material_spec import EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import OperationKind, OperationRole, ProcedureMaterialRole

_PROCEDURES = {
    "isopentyl": _ISOPENTYL_PROCEDURE,
    "aspirin": _ASPIRIN_PROCEDURE,
    "paracetamol": _PARACETAMOL_PROCEDURE,
}

_TIME = re.compile(r"\b(?:min|mins|minute|minutes|hr|hrs|hour|hours|second|seconds|overnight)\b", re.IGNORECASE)
_BATH = re.compile(r"\bbath\b", re.IGNORECASE)
_AGITATE = re.compile(r"\b(?:stir|stirs|stirred|stirring|swirl|swirls|swirled|swirling|shake|shaken|shaking)\b",
                      re.IGNORECASE)
_VACUUM = re.compile(r"\b(?:vacuum|suction|aspirator)\b", re.IGNORECASE)


def _prose(field) -> "str | None":
    """The PRESENT string value of an EvidenceField, else None (an Interval is typed, not prose)."""
    if field is None or not field.is_present or not isinstance(field.value, str):
        return None
    return field.value


def _typed_duration(op) -> bool:
    return op.duration is not None and op.duration.is_present and isinstance(op.duration.value, Interval)


# -- D18: every corpus phase is an evidence-graded claim -------------------------------------------------------

@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_every_corpus_use_phase_is_an_evidence_graded_claim(record: str) -> None:
    for op in _PROCEDURES[record].operations:
        for use in op.material_uses:
            if use.phase is None:
                continue
            assert type(use.phase) is PhaseClaim, (record, op.ordinal, use.name)
            assert use.phase.evidence is not EvidenceKind.UNKNOWN, (record, op.ordinal, use.name)
            # the only two kinds an AUTHORED requirement phase can honestly carry
            assert use.phase.evidence in (EvidenceKind.SOURCE_QUOTED, EvidenceKind.AUTHOR_INFERRED)
            assert use.phase.note.strip(), (record, op.ordinal, use.name)
            if use.phase.evidence is EvidenceKind.SOURCE_QUOTED:
                # a quoted phase must cite the page's own words
                assert use.phase.note.startswith("page:"), (record, op.ordinal, use.name, use.phase.note)


def test_the_curated_source_quoted_phases_are_exactly_the_quoted_ones() -> None:
    """Pinned census: a phase is SOURCE_QUOTED only where the cited page says it. Any upgrade must edit this table
    WITH a quote -- an author cannot quietly promote an inference."""
    quoted = sorted(
        (record, use.name)
        for record, proc in _PROCEDURES.items()
        for op in proc.operations for use in op.material_uses
        if use.phase is not None and use.phase.evidence is EvidenceKind.SOURCE_QUOTED)
    assert quoted == [
        ("aspirin", "sodium bicarbonate"),       # "a saturated aqueous sodium bicarbonate solution"
        ("isopentyl", "sodium bicarbonate"),     # "5% aqueous sodium bicarbonate" (same page, questions section)
        ("isopentyl", "sodium bicarbonate"),     # (two draws, same claim)
        ("isopentyl", "sodium chloride"),        # "saturated aqueous sodium chloride"
    ]


def test_the_isopentyl_bicarbonate_phase_is_quoted_not_an_author_inference() -> None:
    """The Round-V comment called AQUEOUS an author inference; the cited page names this wash reagent '5% aqueous
    sodium bicarbonate' itself (fetched page, questions section)."""
    uses = [u for op in _ISOPENTYL_PROCEDURE.operations for u in op.material_uses if u.name == "sodium bicarbonate"]
    assert len(uses) == 2
    for use in uses:
        assert use.phase.phase is Phase.AQUEOUS_SOLUTION
        assert use.phase.evidence is EvidenceKind.SOURCE_QUOTED
        assert "5% aqueous sodium bicarbonate" in use.phase.note


def test_a_phase_claim_refuses_unknown_and_its_evidence_moves_the_digest() -> None:
    with pytest.raises(ValueError):
        PhaseClaim(Phase.UNKNOWN, EvidenceKind.AUTHOR_INFERRED)
    with pytest.raises(TypeError):
        PhaseClaim("LIQUID", EvidenceKind.SOURCE_QUOTED)  # type: ignore[arg-type]
    assert (PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED).digest
            != PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED).digest)


# -- D16: each prose fragment is filed in its OWNING field -----------------------------------------------------

@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_no_time_words_outside_an_op_that_types_its_duration(record: str) -> None:
    """A time demand belongs in ``duration`` (PROCESS). It may be restated in a temperature/quantity/endpoint slot
    ONLY on an op whose duration is typed minutes (a display restatement of a typed fact, never the fact itself)."""
    for op in _PROCEDURES[record].operations:
        if _typed_duration(op):
            continue
        for slot in ("temperature", "quantity", "endpoint"):
            text = _prose(getattr(op, slot))
            assert text is None or not _TIME.search(text), (record, op.ordinal, slot, text)


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_quantity_slots_carry_no_bath_agitation_or_vacuum_demand(record: str) -> None:
    """``quantity`` is an AMOUNT slot. A bath is a temperature demand, stirring an agitation demand, vacuum a pressure
    demand -- each has its own owning field (D16)."""
    for op in _PROCEDURES[record].operations:
        text = _prose(op.quantity)
        if text is None:
            continue
        for pattern in (_BATH, _AGITATE, _VACUUM):
            assert not pattern.search(text), (record, op.ordinal, text, pattern.pattern)


def test_paracetamol_charcoal_swirl_time_is_a_typed_interval_and_its_other_demands_are_filed() -> None:
    op2 = _PARACETAMOL_PROCEDURE.operations[1]
    assert op2.ordinal == 2 and op2.kind is OperationKind.ADD
    assert op2.duration.value == Interval(4.0, 8.0, "min")      # "for 4-8 minutes": both ends quoted -> exact
    assert _prose(op2.quantity) == "0.3-0.4 g Norit"
    assert _prose(op2.agitation) == "swirl"
    assert _prose(op2.temperature) == "steam bath"


def test_approximate_and_open_ended_durations_stay_prose_never_a_guessed_interval() -> None:
    para6 = _PARACETAMOL_PROCEDURE.operations[5]
    assert para6.ordinal == 6 and _prose(para6.duration) == "sit ~1 hour"     # approximate
    asp2 = _ASPIRIN_PROCEDURE.operations[1]
    assert asp2.ordinal == 2 and _prose(asp2.duration) == "at least 10 minutes"  # open-ended (no finite ceiling)


def test_every_sourced_vacuum_step_reaches_the_pressure_slot() -> None:
    """P-X3: the vacuum filtrations/drying the pages specify are sub-ambient PRESSURE demands, filed as such."""
    filed = sorted(
        (record, op.ordinal) for record, proc in _PROCEDURES.items() for op in proc.operations
        if _prose(op.pressure) is not None and _VACUUM.search(_prose(op.pressure)))
    assert filed == [("aspirin", 4), ("aspirin", 9), ("aspirin", 12), ("paracetamol", 7), ("paracetamol", 9)]


# -- D16: verification text <-> VERIFY ops (P5b) and summary technique <-> ops ----------------------------------

#: (method phrase in ``analytical_verification``, what carries it). "percent yield" is arithmetic over MASS (Round
#: III decision 5), carried by the balance; the ferric-chloride test is reagent + eye -- carried by its OWN VERIFY op
#: as a raw material with NO instrument (never a fabricated one).
_VERIFICATION_PAIRING = {
    "isopentyl": {
        "weigh": ("apparatus", "analytical balance"),
        "percent yield": ("apparatus", "analytical balance"),
        "infrared spectrum": ("apparatus", "infrared spectrometer"),
    },
    "aspirin": {
        "weigh": ("apparatus", "analytical balance"),
        "melting point": ("apparatus", "melting point apparatus"),
        "percent yield": ("apparatus", "analytical balance"),
        "ferric-chloride purity test": ("materials", "ferric chloride"),
    },
    "paracetamol": {
        "weigh": ("apparatus", "analytical balance"),
        "melting point": ("apparatus", "melting point apparatus"),
        "percent yield": ("apparatus", "analytical balance"),
    },
}


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_every_named_verification_method_is_carried_by_a_verify_op(record: str) -> None:
    proc = _PROCEDURES[record]
    text = proc.analytical_verification.value
    verify_ops = [op for op in proc.operations if op.kind is OperationKind.VERIFY]
    carried: "set[tuple[str, str]]" = set()
    for op in verify_ops:
        carried |= {("apparatus", a) for a in op.apparatus} | {("materials", m) for m in op.materials}
    for phrase, carrier in _VERIFICATION_PAIRING[record].items():
        assert phrase in text, (record, phrase, text)          # the table tracks the record's own words
        assert carrier in carried, (record, phrase, carrier)
    # and no VERIFY op is an orphan: each carries at least one paired method
    paired = set(_VERIFICATION_PAIRING[record].values())
    for op in verify_ops:
        mine = {("apparatus", a) for a in op.apparatus} | {("materials", m) for m in op.materials}
        assert mine & paired, (record, op.ordinal)


#: whole-procedure summary field -> (a phrase the summary uses, predicate over ops that must realize it).
_SUMMARY_PAIRING = {
    "isopentyl": [
        ("separation", "separatory funnel", lambda op: op.kind is OperationKind.SEPARATE
         and "separatory funnel" in op.apparatus),
        ("wash", "NaHCO3", lambda op: op.role is OperationRole.WASH
         and any(u.name == "sodium bicarbonate" for u in op.material_uses)),
        ("wash", "saturated NaCl", lambda op: op.role is OperationRole.WASH
         and any(u.name == "sodium chloride" for u in op.material_uses)),
        ("drying", "magnesium sulfate", lambda op: op.kind is OperationKind.DRY
         and any(u.name == "magnesium sulfate" for u in op.material_uses)),
        ("purification", "distillation", lambda op: op.kind is OperationKind.DISTILL),
    ],
    "aspirin": [
        ("wash", "cold-water rinses", lambda op: any(u.name == "cold water" for u in op.material_uses)),
        ("wash", "petroleum-ether rinse", lambda op: any(u.name == "petroleum ether" for u in op.material_uses)),
        ("drying", "air dry", lambda op: op.kind is OperationKind.DRY),
        ("purification", "recrystallize from hot ethyl acetate", lambda op: op.role is OperationRole.RECRYSTALLIZATION
         and any(u.name == "ethyl acetate" for u in op.material_uses)),
        ("purification", "bicarbonate/HCl reprecipitation", lambda op: any(
            u.name == "sodium bicarbonate" and u.role is ProcedureMaterialRole.NEUTRALIZE for u in op.material_uses)),
    ],
    "paracetamol": [
        ("wash", "cold water", lambda op: any(u.name == "cold water" for u in op.material_uses)
         or "cold water" in op.materials),
        ("drying", "air dry", lambda op: op.kind is OperationKind.DRY),
        ("purification", "recrystallize from hot water", lambda op: op.role is OperationRole.RECRYSTALLIZATION
         and op.kind is OperationKind.HEAT),
    ],
}


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_every_summary_technique_is_realized_by_a_concrete_op(record: str) -> None:
    """The whole-procedure summaries are PRESENTATION of what the ops do (D16): every technique the summary names
    must be realized by an op, so the summary text can never outrun the typed ops (P9)."""
    proc = _PROCEDURES[record]
    for field, phrase, realizes in _SUMMARY_PAIRING[record]:
        assert phrase in getattr(proc, field).value, (record, field, phrase)
        assert any(realizes(op) for op in proc.operations), (record, field, phrase)


# -- D17 / Part IV: medium is condition prose, never a species -------------------------------------------------

#: every corpus ``envelope.medium`` -> the MATERIAL words it names, each with where that material is typed.
#: Condition words ("neat", "aqueous", "acidic", "reflux", "steam bath", temperatures) are NOT materials.
_MEDIUM_REVIEW = {
    "aqueous, acidic": {},  # no procedure evidence: D17 carries a text-free material_unresolved remainder
    "ketene generated and consumed in situ (not storable)": {"ketene": "balanced reactant (precursor name)"},
    "aqueous or neat; addition/temperature controlled": {},
    "neat; acid-catalyzed (conc. H2SO4); reflux then distillation (134-143 C fraction collected)": {
        "conc. H2SO4": "typed CATALYST use 'sulfuric acid'"},
    "warm water bath (60-65 C); Fischer esterification of salicylic acid with methanol": {
        "salicylic acid": "balanced reactant (precursor name)", "methanol": "balanced reactant (precursor name)"},
    "steam bath; acetylation of salicylic acid with acetic anhydride (acid-catalyzed)": {
        "salicylic acid": "balanced reactant (precursor name)",
        "acetic anhydride": "balanced reactant (precursor name)",
        "acid-catalyzed": "typed CATALYST use 'sulfuric acid'"},
}


def test_every_corpus_medium_is_reviewed_and_its_materials_are_typed_elsewhere() -> None:
    media = {rec.envelope.medium: rec for rec in SEED_CONDITIONS.values() if rec.envelope.medium}
    assert set(media) == set(_MEDIUM_REVIEW), "a medium string changed or was added: review it here first"
    for medium, words in _MEDIUM_REVIEW.items():
        rec = media[medium]
        procedure = rec.envelope.procedure
        catalyst_uses = set() if procedure is None else {
            u.name for op in procedure.operations for u in op.material_uses if u.role is ProcedureMaterialRole.CATALYST}
        for word, home in words.items():
            assert word in medium, (medium, word)
            if home.startswith("typed CATALYST use"):
                assert home.split("'")[1] in catalyst_uses, (medium, word, catalyst_uses)
            else:
                assert word in rec.assembly_precursor_names, (medium, word, rec.assembly_precursor_names)


# -- D24.1: op.quantity / scale are DISPLAY only when byte-equal to the canonical rendering of the typed fields -----

def _render_op_quantity(op) -> str:
    """The §7.5 D24.1 canonical rendering, restated here from the barrier text (the compiler's renderer lives in
    ``smartchem/capability/coverage.py``; this lint pins the AUTHORED data against the frozen FORMAT, independently)."""
    return " + ".join(f"{u.quantity.value} {u.quantity.unit} {u.name}" for u in op.material_uses if u.quantity is not None)


def _render_scale(procedure) -> str:
    return " + ".join(f"{u.quantity.value} {u.quantity.unit} {u.name}" for op in procedure.operations
                      for u in op.material_uses
                      if u.quantity is not None and u.role in (ProcedureMaterialRole.SUBSTRATE,
                                                              ProcedureMaterialRole.REACTANT))


#: record -> the op ordinals whose ``quantity`` is AUTHORED as the canonical rendering (every word of the original
#: source phrase is typed on that op's uses: quantities, names, formulation words + specifications). Every OTHER
#: PRESENT op.quantity is prose carrying more than the typed uses (an instruction, an apparatus, an untyped material,
#: a purpose) and therefore reads as an unread MATERIAL demand -- honest, never re-authored into a false equality.
_CANONICAL_QUANTITY_OPS = {"isopentyl": {1, 5, 6, 8}, "aspirin": set(), "paracetamol": set()}


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_d24_1_the_canonical_op_quantities_are_exactly_the_curated_ones(record: str) -> None:
    proc = _PROCEDURES[record]
    canonical = {op.ordinal for op in proc.operations
                 if (text := _prose(op.quantity)) is not None and text == _render_op_quantity(op)}
    assert canonical == _CANONICAL_QUANTITY_OPS[record], (record, canonical)
    for op in proc.operations:
        if op.ordinal in _CANONICAL_QUANTITY_OPS[record]:
            assert _render_op_quantity(op), (record, op.ordinal)  # never an empty-equals-empty coincidence


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_d24_1_every_corpus_scale_stays_source_prose(record: str) -> None:
    """No corpus ``scale`` is re-authored: each source scale states masses/moles/ratios/catalyst amounts beyond the
    quantified SUBSTRATE/REACTANT uses, so it honestly reads as an unread demand rather than a forced equality."""
    proc = _PROCEDURES[record]
    assert proc.scale.is_present
    assert proc.scale.value != _render_scale(proc)


def test_d24_16_no_authored_fractional_distillation_overclaim_remains() -> None:
    """D24.16: the isopentyl page says "Set up the distillation apparatus as described by your instructor ... collect
    the fraction between 134 and 143 C" -- a boiling-range cut, never a fractionating column. No authored corpus text
    (summary values, N/A justifications, the envelope medium) may claim FRACTIONAL distillation."""
    rec = _record_for("isopentyl acetate", _ISOPENTYL_PROCEDURE)
    texts = [rec.envelope.medium or ""]
    for name in ("scale", "quench", "workup_isolation", "separation", "wash", "drying", "purification",
                 "analytical_verification"):
        fld = getattr(_ISOPENTYL_PROCEDURE, name)
        texts += [fld.value if isinstance(fld.value, str) else "", fld.justification]
    for op in _ISOPENTYL_PROCEDURE.operations:
        texts += [f.value for f in (op.quantity, op.endpoint, op.temperature) if f is not None and isinstance(f.value, str)]
    assert not [t for t in texts if "fractional" in t.lower()]
    assert "134 and 143" in _ISOPENTYL_PROCEDURE.purification.value


# -- D14 data + completeness preserved -------------------------------------------------------------------------

def _record_for(target: str, procedure):
    return next(rec for rec in SEED_CONDITIONS.values()
                if rec.assembly_target_name == target and rec.envelope.procedure is procedure)


def test_isopentyl_whole_step_peak_is_unknown_not_the_distillate_head_temperature() -> None:
    """P-X2: 134-143 C is the distillate HEAD range -- a lower bound on the heat demand, not a whole-step peak."""
    process = _record_for("isopentyl acetate", _ISOPENTYL_PROCEDURE).envelope.process
    assert process.peak_temperature_k is None
    assert process.min_pressure_atm == 1.0 and process.max_pressure_atm == 1.0  # untouched
    distill = _ISOPENTYL_PROCEDURE.operations[8]
    assert distill.kind is OperationKind.DISTILL
    assert _prose(distill.endpoint) == "collect the fraction between 134 and 143 C"  # the head range stays quoted
    assert distill.temperature is None  # never re-typed as the op's heat demand (it is a vapour temperature)


def test_aspirin_whole_step_minimum_pressure_is_unknown_because_it_vacuum_filters() -> None:
    """P-X3: the record declares whole-step extrema INCLUDING workup; the page vacuum-filters."""
    process = _record_for("aspirin", _ASPIRIN_PROCEDURE).envelope.process
    assert process.min_pressure_atm is None
    assert process.max_pressure_atm == 1.0 and process.peak_temperature_k == 373.15  # untouched


def test_aspirin_ferric_chloride_test_is_its_own_verify_op_with_no_fabricated_instrument() -> None:
    last = _ASPIRIN_PROCEDURE.operations[-1]
    assert (last.ordinal, last.kind, last.apparatus, last.materials) == (
        15, OperationKind.VERIFY, (), ("ferric chloride",))
    assert last.material_uses == ()  # raw source text: D13 carries it as an UNRESOLVED material, never FIT


@pytest.mark.parametrize("record", sorted(_PROCEDURES))
def test_refiling_preserves_procedure_completeness(record: str) -> None:
    """Re-filing moves words between slots; it must not move any readiness tier (completeness is its input)."""
    assert procedure_representation_is_complete(_PROCEDURES[record])
