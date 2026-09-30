"""0.9.5 S10 -- the StreamDisposition vocabulary + binding half (freeze §6; Lane C hostile cases H1-H8, H13, H15, H20).

What is pinned here: the CLOSED subject/value vocabulary, construction-time refusals (evidence, L2 kind x value, the
category/via_op shape), the ``ProcedureEvidence`` placement (digest-covered, canonically sorted, duplicate subject
refused, ``via_op`` names a recovery op), the ``ExperimentStep`` binding (foreign signature, vanished subject, a
CONSUMED_COMPLETELY the reaction does not support -- refused, never rebound), ``reaction_signature`` (resonance-invariant,
isomer-exact), the leaf property and the coverage ledger. The waste CONSUMPTION half (discharge, L1/L3, fate
compatibility, the witness) belongs to the capability-integration writer and is deliberately absent.

Every expectation below is written from the frozen spec, not read back off the module under test -- a check derived
from its own subject certifies its own bugs.
"""
from __future__ import annotations

import dataclasses as dc
import subprocess
import sys
from enum import Enum
from pathlib import Path

import pytest

from smartchem.capability.coverage import FIELD_COVERAGE, FieldOwner, missing_coverage
from smartchem.capability.enums import WasteCapability
from smartchem.category import Bond, Molecule
from smartchem.conditions import ConditionEnvelope
from smartchem.contracts import canonical_digest
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep, StepError
from smartchem.experiment.stock import Phase, StockQuantity
from smartchem.material_spec import EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.stream_disposition import (
    DispositionValue,
    StreamDisposition,
    StreamSubject,
    SubjectKind,
    op_core,
    reaction_signature,
    species_key,
    stream_subjects,
    use_core,
)

_REPO = Path(__file__).resolve().parents[1]
_METHANOL, _ACETIC, _WATER, _MEOAC = (parse_smiles(s) for s in ("CO", "CC(=O)O", "O", "CC(=O)OC"))
_URL = "https://example.test/synthetic-stream-disposition"
_SRC = SourceCitation(_URL, SourceReview.ACCEPTED)
_UNK = EvidenceField.unknown()
_SQ = EvidenceKind.SOURCE_QUOTED
_SQ_LIQUID = PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED)
_CC, _REC, _ROUTED = DispositionValue.CONSUMED_COMPLETELY, DispositionValue.RECOVERED, DispositionValue.ROUTED


def _use(name, role, identity=None, source="fixture stream disposition"):
    return ProcedureMaterialUse(name=name, role=role, identity=identity, phase=_SQ_LIQUID,
                                quantity=StockQuantity.of("10", "mL"), evidence_source=source)


def _ops(*, locator="fixture", apparatus=("round-bottom flask",), extra_reaction_uses=()):
    """ADD(REACTION: methanol SUBSTRATE, acetic acid REACTANT, sulfuric acid CATALYST) / HOLD / SEPARATE+WASH (two
    identical bicarbonate WASH uses -- D-C1) / DRY (MgSO4 DRY use) / DISTILL / VERIFY."""
    return (
        ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, apparatus=apparatus,
                           material_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL),
                                          _use("acetic acid", ProcedureMaterialRole.REACTANT, _ACETIC),
                                          _use("sulfuric acid", ProcedureMaterialRole.CATALYST))
                           + tuple(extra_reaction_uses), locator=locator),
        ProcedureOperation(ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION, locator=locator),
        ProcedureOperation(ordinal=3, kind=OperationKind.SEPARATE, role=OperationRole.WASH, locator=locator,
                           material_uses=(_use("sodium bicarbonate", ProcedureMaterialRole.WASH),
                                          _use("sodium bicarbonate", ProcedureMaterialRole.WASH))),
        ProcedureOperation(ordinal=4, kind=OperationKind.DRY, role=OperationRole.OTHER, locator=locator,
                           material_uses=(_use("magnesium sulfate", ProcedureMaterialRole.DRY),)),
        ProcedureOperation(ordinal=5, kind=OperationKind.DISTILL, role=OperationRole.OTHER, locator=locator),
        ProcedureOperation(ordinal=6, kind=OperationKind.VERIFY, role=OperationRole.OTHER, locator=locator),
    )


def _procedure(ops=None, dispositions=(), **kw):
    fields = dict(reaction_scope="synthetic S10 fixture", source=_SRC, scale=_UNK,
                  operations=_ops() if ops is None else ops, quench=_UNK, workup_isolation=_UNK, separation=_UNK,
                  wash=_UNK, drying=_UNK, purification=_UNK, analytical_verification=_UNK,
                  stream_dispositions=tuple(dispositions))
    fields.update(kw)
    return ProcedureEvidence(**fields)


def _step(procedure=None, *, reactants=(_ACETIC, _METHANOL), products=(_MEOAC, _WATER), target=_MEOAC):
    return ExperimentStep(STEP_SCHEMA, target, tuple(reactants), tuple(products), (),
                          ConditionEnvelope(procedure=_procedure() if procedure is None else procedure))


_BASE = _step()
_SIG = reaction_signature(_BASE)


def _subject(kind, *, ordinal=None, index=None, core=None, sig=_SIG):
    return StreamSubject(kind, sig, ordinal, index, core)


def _byproduct_water():
    return _subject(SubjectKind.BYPRODUCT, core=species_key(_WATER, "water"))


def _residual(identity, name):
    return _subject(SubjectKind.RESIDUAL, core=species_key(identity, name))


def _op_stream(ordinal, ops=None):
    op = (_ops() if ops is None else ops)[ordinal - 1]
    return _subject(SubjectKind.OP_STREAM, ordinal=ordinal, core=op_core(op))


def _use_stream(ordinal, index, ops=None):
    op = (_ops() if ops is None else ops)[ordinal - 1]
    return _subject(SubjectKind.USE_STREAM, ordinal=ordinal, index=index, core=use_core(op.material_uses[index]))


def _d(subject, value=_ROUTED, *, evidence=_SQ, locator=_URL, category=None, via_op=None):
    if value is _ROUTED and category is None:
        category = WasteCapability.AQUEOUS_NEUTRAL
    return StreamDisposition(subject, value, evidence, locator, category=category, via_op=via_op)


def _valid_set():
    """One of each legal shape, all bound to _BASE."""
    return (
        _d(_byproduct_water()),                                                  # BYPRODUCT ROUTED
        _d(_residual(_METHANOL, "methanol"), _CC),                               # RESIDUAL CONSUMED_COMPLETELY
        _d(_residual(None, "sulfuric acid"), _REC, via_op=5),                    # RESIDUAL (catalyst) RECOVERED
        _d(_op_stream(3), category=WasteCapability.HAZARDOUS),                   # OP_STREAM ROUTED
        _d(_use_stream(4, 0), _REC, via_op=3),                                   # USE_STREAM RECOVERED
    )


# -- the closed vocabulary ----------------------------------------------------------------------------------------------

def test_the_vocabulary_is_closed_at_four_kinds_and_three_values():
    assert {k.value for k in SubjectKind} == {"BYPRODUCT", "RESIDUAL", "OP_STREAM", "USE_STREAM"}
    assert {v.value for v in DispositionValue} == {"CONSUMED_COMPLETELY", "RECOVERED", "ROUTED"}


def test_the_fixture_step_has_exactly_the_expected_subject_universe():
    # Written from the fixture, not from stream_subjects: 1 byproduct (water), 3 residual species (methanol, acetic
    # acid, sulfuric acid), 3 spent-stream ops (SEPARATE/WASH, DRY, DISTILL), 3 spent-stream uses (2 bicarbonate WASH,
    # 1 MgSO4 DRY). The two textually identical WASH uses are TWO subjects (D-C1: one statement never covers two).
    expected = {
        _byproduct_water(), _residual(_METHANOL, "methanol"), _residual(_ACETIC, "acetic acid"),
        _residual(None, "sulfuric acid"), _op_stream(3), _op_stream(4), _op_stream(5),
        _use_stream(3, 0), _use_stream(3, 1), _use_stream(4, 0),
    }
    assert set(stream_subjects(_BASE)) == expected
    assert len(stream_subjects(_BASE)) == 10
    assert _use_stream(3, 0) != _use_stream(3, 1)


# -- construction-time refusals (StreamDisposition) -----------------------------------------------------------------------

_NON_CERTIFYING = [k for k in EvidenceKind if k is not EvidenceKind.SOURCE_QUOTED]


def test_the_non_certifying_list_is_exactly_the_six_barrier_kinds():
    assert {k.value for k in _NON_CERTIFYING} == {"AUTHOR_INFERRED", "ASSUMED", "USER_DECLARED", "UNKNOWN", "DERIVED",
                                                  "CLAMPED"}


@pytest.mark.parametrize("evidence", _NON_CERTIFYING, ids=lambda k: k.value)
def test_every_non_certifying_evidence_kind_is_refused_at_construction(evidence):
    with pytest.raises(ValueError, match="SOURCE_QUOTED"):
        _d(_byproduct_water(), evidence=evidence)
    _d(_byproduct_water())  # the SOURCE_QUOTED twin constructs (the refusal is about the kind, not the shape)


@pytest.mark.parametrize("locator", ["", "   "])
def test_an_empty_locator_is_refused(locator):
    with pytest.raises(ValueError, match="locator"):
        _d(_byproduct_water(), locator=locator)


#: LAW L2, transcribed from freeze §6 (NOT imported from the module).
_L2 = {
    _CC: {SubjectKind.RESIDUAL},
    _REC: {SubjectKind.RESIDUAL, SubjectKind.USE_STREAM},
    _ROUTED: {SubjectKind.BYPRODUCT, SubjectKind.RESIDUAL, SubjectKind.OP_STREAM, SubjectKind.USE_STREAM},
}
_SUBJECT_OF = {
    SubjectKind.BYPRODUCT: _byproduct_water,
    SubjectKind.RESIDUAL: lambda: _residual(_METHANOL, "methanol"),
    SubjectKind.OP_STREAM: lambda: _op_stream(3),
    SubjectKind.USE_STREAM: lambda: _use_stream(4, 0),
}


@pytest.mark.parametrize("value,kind", [(v, k) for v in DispositionValue for k in SubjectKind],
                         ids=lambda x: x.value)
def test_the_kind_by_value_table_is_exactly_l2(value, kind):
    build = lambda: _d(_SUBJECT_OF[kind](), value, via_op=5 if value is _REC else None)  # noqa: E731
    if kind in _L2[value]:
        assert build().subject.kind is kind
    else:
        with pytest.raises(ValueError, match="L2"):
            build()


def test_consumed_completely_on_a_byproduct_is_refused():
    with pytest.raises(ValueError, match="CONSUMED_COMPLETELY may not name a BYPRODUCT"):
        _d(_byproduct_water(), _CC)


def test_recovered_on_a_byproduct_is_refused_even_with_a_recovery_op():
    with pytest.raises(ValueError, match="RECOVERED may not name a BYPRODUCT"):
        _d(_byproduct_water(), _REC, via_op=5)


def test_recovered_without_via_op_is_refused():
    with pytest.raises(ValueError, match="via_op"):
        _d(_residual(_METHANOL, "methanol"), _REC)
    with pytest.raises(ValueError, match="via_op"):
        _d(_residual(_METHANOL, "methanol"), _REC, via_op=True)  # a bool is not an ordinal


def test_the_category_and_via_op_shapes_are_exact():
    with pytest.raises(TypeError, match="WasteCapability"):
        StreamDisposition(_byproduct_water(), _ROUTED, _SQ, _URL)                   # ROUTED without a category
    with pytest.raises(TypeError, match="WasteCapability"):
        _d(_byproduct_water(), category="AQUEOUS_NEUTRAL")                          # the bare value is not the enum

    class WasteCapabilityLookalike(str, Enum):
        AQUEOUS_NEUTRAL = "AQUEOUS_NEUTRAL"

    with pytest.raises(TypeError, match="WasteCapability"):
        _d(_byproduct_water(), category=WasteCapabilityLookalike.AQUEOUS_NEUTRAL)   # same value, wrong class
    with pytest.raises(ValueError, match="only ROUTED carries a category"):
        _d(_residual(_METHANOL, "methanol"), _CC, category=WasteCapability.HAZARDOUS)
    with pytest.raises(ValueError, match="only RECOVERED names a via_op"):
        _d(_byproduct_water(), via_op=5)


# -- placement: ProcedureEvidence ------------------------------------------------------------------------------------------

def test_a_duplicate_subject_is_refused_even_with_different_values():
    subject = _residual(_METHANOL, "methanol")
    with pytest.raises(ValueError, match="same subject"):
        _procedure(dispositions=(_d(subject, _CC), _d(subject, category=WasteCapability.HAZARDOUS)))


@pytest.mark.parametrize("via_op", [1, 2, 4, 6, 7], ids=lambda n: f"op{n}")
def test_recovered_via_op_must_name_a_distill_filter_or_separate_op_of_this_procedure(via_op):
    # ops 1 ADD, 2 HOLD, 4 DRY, 6 VERIFY are not recovery ops; op 7 does not exist.
    with pytest.raises(ValueError, match="DISTILL/FILTER/SEPARATE"):
        _procedure(dispositions=(_d(_use_stream(4, 0), _REC, via_op=via_op),))


@pytest.mark.parametrize("via_op", [3, 5], ids=["SEPARATE", "DISTILL"])
def test_recovered_via_a_real_recovery_op_constructs(via_op):
    assert _procedure(dispositions=(_d(_use_stream(4, 0), _REC, via_op=via_op),)).stream_dispositions


def test_stream_dispositions_must_be_a_tuple_of_stream_dispositions():
    with pytest.raises(TypeError, match="tuple"):
        dc.replace(_procedure(), stream_dispositions=list(_valid_set()))
    with pytest.raises(TypeError):
        _procedure(dispositions=("ROUTED",))


def test_the_default_is_empty_and_positional_callers_still_build():
    positional = ProcedureEvidence("synthetic S10 fixture", _SRC, _UNK, _ops(), _UNK, _UNK, _UNK, _UNK, _UNK, _UNK,
                                   _UNK)
    assert positional.stream_dispositions == ()
    assert positional == _procedure()


def test_canonical_sort_makes_insertion_order_irrelevant():
    forward, backward = _valid_set(), tuple(reversed(_valid_set()))
    assert forward != backward
    a, b = _procedure(dispositions=forward), _procedure(dispositions=backward)
    assert a.stream_dispositions == b.stream_dispositions
    assert a == b and a.digest == b.digest
    assert _step(a).digest == _step(b).digest


def test_a_disposition_moves_the_procedure_and_step_digests():
    bare = _procedure()
    one = _procedure(dispositions=(_d(_byproduct_water()),))
    other_category = _procedure(dispositions=(_d(_byproduct_water(), category=WasteCapability.HAZARDOUS),))
    digests = {bare.digest, one.digest, other_category.digest}
    assert len(digests) == 3, "stream_dispositions must be digest-covered (compare=True), value and category included"
    assert len({_step(bare).digest, _step(one).digest, _step(other_category).digest}) == 3


# -- binding: ExperimentStep -------------------------------------------------------------------------------------------------

def test_a_valid_disposition_set_binds():
    step = _step(_procedure(dispositions=_valid_set()))
    assert len(step.envelope.procedure.stream_dispositions) == 5


@pytest.mark.parametrize("subject", [
    _subject(SubjectKind.BYPRODUCT, core=species_key(_METHANOL, "methanol")),        # a species that is no byproduct
    _subject(SubjectKind.RESIDUAL, core=species_key(parse_smiles("CCO"), "ethanol")),  # no typed use of that species
    _subject(SubjectKind.RESIDUAL, core="name:acetic acid"),                         # right name, wrong key (identity)
    _subject(SubjectKind.OP_STREAM, ordinal=9, core=op_core(_ops()[2])),             # ordinal beyond the procedure
    _subject(SubjectKind.OP_STREAM, ordinal=6, core=op_core(_ops()[5])),             # VERIFY is not a spent-stream op
    _subject(SubjectKind.USE_STREAM, ordinal=3, index=2, core=use_core(_ops()[2].material_uses[0])),  # index beyond
    _subject(SubjectKind.USE_STREAM, ordinal=4, index=0, core=use_core(_ops()[2].material_uses[0])),  # wrong core
], ids=["byproduct-not-produced", "residual-no-use", "residual-name-key", "op-ordinal-9", "op-not-spent",
        "use-index-2", "use-wrong-core"])
def test_an_unknown_subject_is_refused_by_the_step(subject):
    procedure = _procedure(dispositions=(_d(subject),))
    with pytest.raises(StepError, match="does not exist in this step"):
        _step(procedure)


def test_a_transplanted_signature_is_refused():
    # H7: the same structural subject, signed by a DIFFERENT reaction (ethyl acetate esterification also yields water).
    foreign = reaction_signature(ExperimentStep(
        STEP_SCHEMA, parse_smiles("CCOC(C)=O"), (_ACETIC, parse_smiles("CCO")), (parse_smiles("CCOC(C)=O"), _WATER),
        (), ConditionEnvelope()))
    assert foreign != _SIG
    procedure = _procedure(dispositions=(_d(_subject(SubjectKind.BYPRODUCT, core=species_key(_WATER, "water"),
                                                     sig=foreign)),))
    with pytest.raises(StepError, match="never transplanted"):
        _step(procedure)


def test_reordering_two_spent_stream_ops_makes_the_subject_vanish_never_rebinds():
    # H6 / M-SD10: SEPARATE (#3) <-> DRY (#4), both spent-stream kinds. The OP_STREAM disposition written for the
    # SEPARATE op at ordinal 3 must NOT silently discharge the DRY op that now sits at ordinal 3.
    ops = _ops()
    swapped = (ops[0], ops[1], dc.replace(ops[3], ordinal=3), dc.replace(ops[2], ordinal=4), ops[4], ops[5])
    disposition = _d(_op_stream(3))
    _step(_procedure(ops=ops, dispositions=(disposition,)))            # binds in the original order
    with pytest.raises(StepError, match="does not exist in this step"):
        _step(_procedure(ops=swapped, dispositions=(disposition,)))


def test_retyping_a_use_role_makes_its_use_stream_vanish():
    ops = _ops()
    retyped = ops[:3] + (dc.replace(ops[3], material_uses=(_use("magnesium sulfate", ProcedureMaterialRole.RINSE),)),) \
        + ops[4:]
    disposition = _d(_use_stream(4, 0))
    with pytest.raises(StepError, match="does not exist in this step"):
        _step(_procedure(ops=retyped, dispositions=(disposition,)))


def test_consumed_completely_on_a_species_the_step_does_not_net_consume_is_refused():
    # H15: water typed as a REACTANT use -- the RESIDUAL subject exists, but the balanced reaction PRODUCES water.
    ops = _ops(extra_reaction_uses=(_use("water", ProcedureMaterialRole.REACTANT, _WATER),))
    procedure = _procedure(ops=ops, dispositions=(_d(_residual(_WATER, "water"), _CC),))
    with pytest.raises(StepError, match="NET-consumes"):
        _step(procedure)
    _step(_procedure(ops=ops, dispositions=(_d(_residual(_WATER, "water")),)))   # ROUTED on the same subject binds


def test_consumed_completely_on_a_catalyst_or_a_name_keyed_residual_is_refused():
    with pytest.raises(StepError, match="NET-consumes"):
        _step(_procedure(dispositions=(_d(_residual(None, "sulfuric acid"), _CC),)))


def test_consumed_completely_on_a_net_consumed_substrate_binds():
    assert _step(_procedure(dispositions=(_d(_residual(_METHANOL, "methanol"), _CC),)))


def test_a_prose_only_edit_does_not_unbind():
    # locators, apparatus, evidence_source, reaction_scope, evidence_scope and a use's display NAME for a
    # structure-bearing species are presentation: the subject universe and the binding survive all of them.
    ops = _ops(locator="p. 2, para 3", apparatus=("250-mL flask", "stir bar"))
    ops = (dc.replace(ops[0], material_uses=(
        _use("MeOH", ProcedureMaterialRole.SUBSTRATE, _METHANOL, source="reworded"),) + ops[0].material_uses[1:]),) \
        + ops[1:]
    edited = _step(_procedure(ops=ops, reaction_scope="reworded scope", evidence_scope="reworded note"))
    assert stream_subjects(edited) == stream_subjects(_BASE)
    assert _step(_procedure(ops=ops, dispositions=_valid_set(), reaction_scope="reworded scope"))


def test_a_forged_procedure_swapped_into_an_envelope_is_refused_at_step_construction():
    # The wire path decodes a ProcedureEvidence first and the step second; a forgery must die at the step.
    forged = _procedure(dispositions=(_d(_op_stream(3, ops=_ops()), category=WasteCapability.HAZARDOUS),))
    alien = dc.replace(forged, operations=_ops()[:2] + (dc.replace(_ops()[4], ordinal=3),))  # op 3 is now DISTILL
    with pytest.raises(StepError, match="does not exist in this step"):
        _step(alien)


# -- reaction_signature -----------------------------------------------------------------------------------------------------

def _ring_bonds(m: Molecule) -> "list[Bond]":
    """Bonds whose endpoints stay connected without them (ring bonds) -- plain graph surgery, no parser."""
    out = []
    for b in m.bonds:
        adjacency: "dict[int, set[int]]" = {}
        for c in m.bonds:
            if c != b:
                adjacency.setdefault(c.i, set()).add(c.j)
                adjacency.setdefault(c.j, set()).add(c.i)
        seen, stack = {b.i}, [b.i]
        while stack:
            for v in adjacency.get(stack.pop(), ()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if b.j in seen:
            out.append(b)
    return out


def _kekule_alternate(m: Molecule) -> Molecule:
    """The OTHER Kekulé placement of a single benzene ring, built by flipping ring bond orders 1<->2 -- a graph the
    SMILES parser never sees (a SMILES-spelling pair is canonicalised by the parser: a vacuous control)."""
    ring = {b for b in _ring_bonds(m) if b.order in (1, 2)}
    return Molecule(m.atoms, frozenset([b for b in m.bonds if b not in ring] + [Bond(b.i, b.j, 3 - b.order)
                                                                                 for b in ring]), m.charge, m.state)


_O_XYLENE, _CL2, _HCL = parse_smiles("Cc1ccccc1C"), parse_smiles("ClCl"), parse_smiles("Cl")
_CHLORO_O_XYLENE = parse_smiles("Cc1ccc(Cl)cc1C")


def test_the_kekule_alternate_is_a_discriminating_control():
    alt = _kekule_alternate(_O_XYLENE)
    assert alt.bonds != _O_XYLENE.bonds
    # the literal canonical digest SPLITS the pair (so a resonance-blind signature would fail the next test)...
    assert canonical_digest(alt.canonical()) != canonical_digest(_O_XYLENE.canonical())
    # ...and resonance_identity merges it.
    assert resonance_identity(alt) == resonance_identity(_O_XYLENE)


def test_reaction_signature_is_resonance_invariant_and_the_binding_follows_it():
    def chlorination(xylene):
        return ExperimentStep(STEP_SCHEMA, _CHLORO_O_XYLENE, (xylene, _CL2), (_CHLORO_O_XYLENE, _HCL), (),
                              ConditionEnvelope())

    parsed, alternate = chlorination(_O_XYLENE), chlorination(_kekule_alternate(_O_XYLENE))
    assert parsed.digest != alternate.digest           # genuinely different step values...
    assert reaction_signature(parsed) == reaction_signature(alternate)   # ...one reaction
    # a BYPRODUCT disposition written against the parsed spelling binds on the Kekulé-alternate step
    sig = reaction_signature(parsed)
    subject = StreamSubject(SubjectKind.BYPRODUCT, sig, None, None, species_key(_HCL, "hydrogen chloride"))
    ops = (ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, locator="fixture"),)
    procedure = _procedure(ops=ops, dispositions=(_d(subject, category=WasteCapability.OFFGAS_CAPTURE),))
    ExperimentStep(STEP_SCHEMA, _CHLORO_O_XYLENE, (_kekule_alternate(_O_XYLENE), _CL2), (_CHLORO_O_XYLENE, _HCL), (),
                   ConditionEnvelope(procedure=procedure))


@pytest.mark.parametrize("a,b", [("Cc1ccccc1C", "Cc1cccc(C)c1"), ("Cc1ccccc1C", "Cc1ccc(C)cc1"),
                                 ("Cc1cccc(C)c1", "Cc1ccc(C)cc1"), ("CCO", "COC"), ("CCCO", "CC(C)O")],
                         ids=["o-m-xylene", "o-p-xylene", "m-p-xylene", "ethanol-DME", "propanols"])
def test_reaction_signature_distinguishes_constitutional_isomers(a, b):
    from types import SimpleNamespace

    ma, mb = parse_smiles(a), parse_smiles(b)
    assert reaction_signature(SimpleNamespace(reactants=(ma, _CL2), products=(_HCL,))) != \
        reaction_signature(SimpleNamespace(reactants=(mb, _CL2), products=(_HCL,)))
    assert species_key(ma, "x") != species_key(mb, "x")


def test_reaction_signature_is_a_multiset_digest_blind_to_order_and_envelope():
    from types import SimpleNamespace

    assert reaction_signature(SimpleNamespace(reactants=(_METHANOL, _ACETIC), products=(_WATER, _MEOAC))) == _SIG
    assert reaction_signature(SimpleNamespace(reactants=(_METHANOL, _METHANOL, _ACETIC),
                                              products=(_WATER, _MEOAC))) != _SIG   # multiplicity counts
    assert reaction_signature(_step(_procedure(reaction_scope="another scope"))) == _SIG


# -- the species key is the S7 structure key -----------------------------------------------------------------------------

def test_the_species_key_is_the_s7_structure_key_and_the_name_fold():
    assert species_key(_METHANOL, "ignored") == "struct:" + resonance_identity(_METHANOL)
    # a Kekulé-split pair is ONE species (a literal canonical() key would split it -- the C7-2 false-BLOCKED)
    assert species_key(_kekule_alternate(_O_XYLENE), "a") == species_key(_O_XYLENE, "b")
    # 0.9.5 S18 (C1-3): whitespace folds, case does not -- a subject key is an identity claim
    assert species_key(None, "  Sodium   BICARBONATE ") == "name:Sodium BICARBONATE"


def test_an_asgiven_identity_maps_to_the_struct_asgiven_prefix(monkeypatch):
    import smartchem.smiles as smiles_mod
    from smartchem.experiment import stock

    monkeypatch.setattr(smiles_mod, "resonance_identity", lambda m: "asgiven:" + "0" * 64)
    # the key is stock's now (S7): bypass its memo so the patched canonicaliser is actually consulted
    monkeypatch.setattr(stock, "_structure_key", stock._structure_key.__wrapped__)
    assert species_key(_METHANOL, "x") == "struct-asgiven:" + "0" * 64


def test_the_species_key_is_stock_structure_key():
    from smartchem.experiment import stock

    for m in (_METHANOL, _O_XYLENE, _kekule_alternate(_O_XYLENE), _CHLORO_O_XYLENE):
        assert species_key(m, "x") == stock.structure_key(m)
    # 0.9.5 S18 (C1-3): the name half folds whitespace only -- case is identity ("CO" is not "Co")
    assert species_key(None, "  Sodium   BICARBONATE ") == "name:" + stock.collapse_material_name("Sodium BICARBONATE")
    assert species_key(None, "CO") != species_key(None, "Co")


# -- leaf property, role-table drift guard, coverage ledger ------------------------------------------------------------------

def test_the_module_is_a_leaf_it_never_loads_capability_or_service():
    script = (
        "import sys\n"
        "import smartchem.stream_disposition as sd\n"
        "from smartchem.smiles import parse_smiles\n"
        "from smartchem.material_spec import EvidenceKind\n"
        "s = sd.StreamSubject(sd.SubjectKind.RESIDUAL, '0' * 64, None, None, sd.species_key(parse_smiles('CO'), 'm'))\n"
        "sd.StreamDisposition(s, sd.DispositionValue.CONSUMED_COMPLETELY, EvidenceKind.SOURCE_QUOTED, 'p. 1')\n"
        "try:\n"
        "    sd.StreamDisposition(s, sd.DispositionValue.ROUTED, EvidenceKind.SOURCE_QUOTED, 'p. 1', category='X')\n"
        "    raise SystemExit('a non-enum category constructed')\n"
        "except TypeError:\n"
        "    pass\n"
        "bad = sorted(m for m in sys.modules if m.startswith(('smartchem.capability', 'smartchem.service')))\n"
        "raise SystemExit(repr(bad) if bad else 0)\n"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=_REPO, capture_output=True, text=True, timeout=300,
                            env={"PYTHONPATH": str(_REPO), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_role_tables_have_one_owner_and_waste_imports_them():
    import smartchem.capability.waste as waste
    import smartchem.stream_disposition as sd

    # identity, not equality: one copy of each table, bound into waste under its historical name
    assert sd.SPENT_STREAM_ROLES is waste._SPENT_STREAM_ROLES
    assert sd.SPENT_STREAM_OP_ROLES is waste._SPENT_STREAM_OP_ROLES
    assert sd.SPENT_STREAM_OP_KINDS is waste._SPENT_STREAM_OP_KINDS
    assert sd.CONSUMED_ROLES is waste._CONSUMED_ROLES
    assert sd.CATALYST_ROLES is waste._CATALYST_ROLES


def test_the_new_field_has_a_waste_ledger_row_and_coverage_stays_complete():
    assert missing_coverage() == ()
    assert FIELD_COVERAGE[("ProcedureEvidence", "stream_dispositions")].primary is FieldOwner.WASTE
