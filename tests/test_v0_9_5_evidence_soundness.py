"""0.9.5 S18 -- evidence soundness (Wave C1: a REACHABLE false CAPABILITY_FIT, release-blocking).

Operative note, for whoever opens this after me: every finding below was a route that reached CAPABILITY_FIT on a bench
that could not handle what the route leaves behind. Each regression here FAILS on the pre-S18 tree (d573e39) -- the
docstring of each test says which leg -- and passes on the repaired one. Nothing here edits the witness.

* **C1-1** an envelope catalyst STRING beside a typed CATALYST use: the string was read first with no identity through
  an exact-case name lookup (a miss), then a name-fold de-duplication skipped the typed use whose STRUCTURE carried
  H290/H314 -- more evidence, fewer categories. Laws: a covered string resolves through the cover's identity; dedup
  keys on (species, exact spelling); the hazard name lookup folds; adding evidence never removes a derived category
  and never turns BLOCKED into FIT.
* **C1-2** ROUTED(AQUEOUS_NEUTRAL) on a GHS-toxic methanol residual discharged it with no HAZARDOUS in sight. Law: a
  ROUTED stream still carries its species -- the record's categories are added by the SAME mapping the byproduct and
  catalyst legs use. An OP_STREAM names no species: its category is the only evidence (the stated boundary).
* **C1-3** a typed ``"CO"`` (carbon monoxide) was certified by a ``"Co"`` (cobalt) bottle, and covered a raw ``"Co"``
  string into nonexistence. Law: case-folding is lossy -- a case-only match is a POSSIBLE source at most, never a
  certifying edge, never a cover, never a merge.
* **C1-4** RECOVERED on a LIQUID residual via a gravity FILTER that names nothing discharged it. Law: the ``via_op``
  comes after every op introducing the subject, the subject's phase is CERTIFIED, and the op kind can recover it.

Folded in from Wave C5 (same files, same theme): **C5-F1** a second CATALYST species under a fold-equal name lost its
residual obligation (C1-1's root); **C5-F3** twin-core subjects rebound silently (the op/use cores now cover every typed
field); **C5-F4** a reactant typed only as a rinse had no residual obligation; **C5-F5** = C1-4's ordering leg;
**C5-F6** an identity with no record borrowed the record of its display NAME and passed L3.
"""
from __future__ import annotations

import dataclasses as dc
import itertools

import pytest

from smartchem.capability.assess import _edge
from smartchem.capability.coverage import render_scale, render_summary, render_verification
from smartchem.capability.enums import CapabilityStatus, WasteCapability
from smartchem.capability.quantity import QuantityDemand
from smartchem.capability.requirements import MaterialRequirement, compile_capability_requirements
from smartchem.capability.waste import _RECOVERABLE_PHASES, _hazard_categories, derive_waste
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.data.hazards import HAZARD_REFS, hazards_for_named
from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute, StepError
from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
    collapse_material_name,
    normalize_material_name,
    structure_key,
)
from smartchem.material_spec import ConcentrationBasis, EvidenceKind, MaterialSpecification, PhaseClaim
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
)
from smartchem.stream_disposition import RECOVERY_OP_KINDS, DispositionValue, SubjectKind, stream_subjects

from tests.test_v0_9_5_disposition_consumption import (
    _H2SO4,
    _UNRECORDED_CAT,
    _WITNESS_TABLE,
    _assess,
    _d,
    _dme,
    _dme_subjects,
    _exact_profile,
    _micro,
    _op,
    _sourced_step,
    _statuses,
    _subject_of,
    _with,
    _witness_dispositions,
)
from tests.test_v0_9_round_v_zero_fit_theorem import _ACETIC, _MEOAC, _METHANOL, _URL, _WATER, _maximal_profile, _pure, _use

_ROUTED, _CC, _RECOVERED = DispositionValue.ROUTED, DispositionValue.CONSUMED_COMPLETELY, DispositionValue.RECOVERED
_AN, _HAZ, _OFFGAS = WasteCapability.AQUEOUS_NEUTRAL, WasteCapability.HAZARDOUS, WasteCapability.OFFGAS_CAPTURE
_SQ_SOLID = PhaseClaim(Phase.SOLID, EvidenceKind.SOURCE_QUOTED)


def _rendered(route: ExperimentRoute, operations) -> ExperimentRoute:
    """``route`` (one step) with its procedure's operations replaced and every PRESENT summary field re-rendered from
    the typed carriers (the DME witness's D24.1 contract: prose would be an unread demand)."""
    step = route.steps[0]
    draft = dc.replace(step.envelope.procedure, operations=tuple(operations))
    procedure = dc.replace(draft, scale=EvidenceField.present(render_scale(draft), _URL),
                           workup_isolation=EvidenceField.present(render_summary(draft, "workup_isolation"), _URL),
                           analytical_verification=EvidenceField.present(render_verification(draft), _URL))
    return ExperimentRoute(ROUTE_SCHEMA, (dc.replace(step, envelope=dc.replace(step.envelope, procedure=procedure)),))


def _with_catalysts(route: ExperimentRoute, catalysts) -> ExperimentRoute:
    step = route.steps[0]
    env = dc.replace(step.envelope, catalysts=tuple(catalysts))
    return ExperimentRoute(ROUTE_SCHEMA, (dc.replace(step, envelope=env),))


# =====================================================================================================================
# C1-1 -- an envelope catalyst string can never erase the typed use's structure-resolved hazard
# =====================================================================================================================

def _dme_with_h2so4(*, in_op: int = 1, name: str = "sulfuric acid", identity=_H2SO4) -> ExperimentRoute:
    """The DME witness route with a typed CATALYST use (conc. H2SO4, H290/H314 by STRUCTURE) on op ``in_op``."""
    base = _dme()
    ops = list(base.steps[0].envelope.procedure.operations)
    use = _use(name, ProcedureMaterialRole.CATALYST, identity, qty="1")
    ops[in_op - 1] = dc.replace(ops[in_op - 1], material_uses=ops[in_op - 1].material_uses + (use,))
    return _rendered(base, ops)


def _r6(envelope: tuple, *, in_op: int = 1) -> ExperimentRoute:
    """Wave C1 r6: the typed H2SO4 use + ``envelope`` catalyst strings + the witness dispositions + a RECOVERED on the
    H2SO4 residual (the statement that used to discharge the envelope string's obligation)."""
    route = _with_catalysts(_dme_with_h2so4(in_op=in_op), envelope)
    water = _subject_of(route, SubjectKind.BYPRODUCT)
    op3 = _subject_of(route, SubjectKind.OP_STREAM)
    methanol = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_METHANOL))
    acid = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_H2SO4))
    return _with(route, _d(water), _d(op3), _d(methanol, _CC), _d(acid, _RECOVERED, via_op=3))


def _r6_profile(waste=frozenset({_AN})):
    return dc.replace(_exact_profile(waste), material_inventory=(_pure("methanol-pure", _METHANOL),
                                                                 _pure("h2so4-pure", _H2SO4)),
                      procurement=_maximal_profile(()).procurement)


_ENVELOPE_SPELLINGS = ("sulfuric acid", "Sulfuric acid", "SULFURIC ACID", " sulfuric  acid ", "Sulfuric  Acid")


def test_c1_1_control_the_typed_use_alone_derives_hazardous_and_blocks():
    route = _r6(())
    assert _HAZ in derive_waste(route)[0]
    assert _assess(route, _r6_profile()).overall is CapabilityStatus.BLOCKED


@pytest.mark.parametrize("in_op", [1, 2], ids=["use-before-HOLD", "use-on-HOLD"])
@pytest.mark.parametrize("order", ["alone", "first", "last"])
@pytest.mark.parametrize("spelling", _ENVELOPE_SPELLINGS, ids=repr)
def test_c1_1_r6_an_envelope_string_never_erases_hazardous_nor_reaches_fit(spelling, order, in_op):
    """Pre-S18 FAILS for every non-exact spelling: ``"Sulfuric acid"`` / ``" sulfuric  acid "`` etc. missed the exact-case
    hazard lookup, the name-fold dedup skipped the typed use, and the route was FIT on an AQUEOUS_NEUTRAL-only bench."""
    other = "catalyst x"  # an unrelated uncovered string, to exercise tuple order
    envelope = {"alone": (spelling,), "first": (spelling, other), "last": (other, spelling)}[order]
    route = _r6(envelope, in_op=in_op)
    cats, reasons, _unresolved = derive_waste(route)
    assert _HAZ in cats, reasons
    a = _assess(route, _r6_profile())
    assert not a.is_capability_fit and a.waste.status is CapabilityStatus.BLOCKED


def test_c1_1_a_covered_string_resolves_through_the_cover_identity_never_its_own_name():
    """The string names nothing the hazard table knows ("catalyst q"); the typed use it covers IS H2SO4 by structure.
    Pre-S18 FAILS: the string was resolved with identity=None (no record -> an open obligation) and the typed use was
    name-deduplicated away, so HAZARDOUS was never derived."""
    route = _with_catalysts(_dme_with_h2so4(name="catalyst q"), ("catalyst q",))
    cats, reasons, _u = derive_waste(route)
    assert _HAZ in cats
    assert any("'catalyst q' (step 1 envelope catalyst) is not consumed and carries sourced GHS H290, H314" in r
               for r in reasons), reasons


def test_c1_1_dedup_never_discards_a_second_species_under_the_same_name():
    """Two typed CATALYST uses spelled alike but of DIFFERENT species (an unrecorded one first, H2SO4 second). Pre-S18
    FAILS: the fold-keyed dedup skipped the second use and its H290/H314 record with it."""
    route = _micro(_op(uses=(_use("acid catalyst", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),
                             _use("acid catalyst", ProcedureMaterialRole.CATALYST, _H2SO4))))
    assert _HAZ in derive_waste(route)[0]


def test_c1_1_the_hazard_name_lookup_folds_and_a_miss_stays_unresolved():
    for spelling in _ENVELOPE_SPELLINGS:
        assert hazards_for_named(spelling).ghs_codes == ("H290", "H314"), spelling
    assert hazards_for_named("CO") is None and hazards_for_named("Co") is None  # folds to no record: UNKNOWN
    assert hazards_for_named("H2SO4") is None                                      # a fold is not synonymy
    # every record name is a fixed point of the fold, so the folded query hits exactly the record the name spells
    assert all(normalize_material_name(ref.name) == ref.name for ref in HAZARD_REFS)


def test_c1_1_an_uncovered_case_variant_string_resolves_by_its_own_folded_name():
    """No typed use at all: ``"Sulfuric acid"`` alone. Pre-S18 FAILS: the exact-case lookup missed and the string
    became an 'unknown catalyst' instead of the H2SO4 residual it names."""
    route = _micro(catalysts=("Sulfuric acid",))
    assert _HAZ in derive_waste(route)[0]


# =====================================================================================================================
# C1-2 -- ROUTED discharges one obligation AND still carries its species' hazard categories
# =====================================================================================================================

def _r1(category=_AN) -> ExperimentRoute:
    water, op3, methanol = _dme_subjects()
    return _with(_dme(), _d(water), _d(op3), _d(methanol, category=category))


def test_c1_2_r1_routed_aqueous_neutral_cannot_launder_a_toxic_residual():
    """Pre-S18 FAILS: categories were {AQUEOUS_NEUTRAL} and the route was FIT on the AQUEOUS_NEUTRAL-only bench."""
    cats, reasons, unresolved = derive_waste(_r1())
    assert cats == frozenset({_AN, _HAZ}) and unresolved == ()
    assert any("routed stream carries methanol" in r and "(S18)" in r for r in reasons), reasons
    a = _assess(_r1())
    assert not a.is_capability_fit and a.waste.status is CapabilityStatus.BLOCKED


def test_c1_2_liveness_the_same_routing_fits_a_bench_that_handles_both_categories():
    """The routing is a real DISCHARGE (never a refusal in disguise): with HAZARDOUS handling on the bench it is FIT."""
    a = _assess(_r1(), _exact_profile(frozenset({_AN, _HAZ})))
    assert a.is_capability_fit, _statuses(a)


def test_c1_2_a_routed_hazardous_spent_wash_carries_its_species_too():
    """USE_STREAM: a methanol WASH use (H225/H301/...) routed AQUEOUS_NEUTRAL. Pre-S18 FAILS (no HAZARDOUS)."""
    route = _micro(_op(uses=(_use("methanol", ProcedureMaterialRole.WASH, _METHANOL),)))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    cats, _r, _u = derive_waste(_with(route, _d(stream)))
    assert {_AN, _HAZ} <= cats


def test_c1_2_an_op_stream_names_no_species_so_its_category_is_the_only_evidence():
    """The stated boundary: a ROUTED OP_STREAM adds exactly its SOURCE_QUOTED category (the witness's op #3 filter)."""
    water, op3, methanol = _dme_subjects()
    cats, _r, _u = derive_waste(_with(_dme(), _d(op3, category=_OFFGAS)))
    assert cats == frozenset({_OFFGAS})


def _species_codes(route: ExperimentRoute, subject) -> "tuple[str, ...]":
    """The GHS codes of ``subject``'s species, read INDEPENDENTLY of derive_waste (structure record first; a name record
    only for an identity-less use) -- the oracle the exhaustive check below is measured against."""
    from smartchem.decompiler_review import molecule_hazards

    step = route.steps[0]
    if subject.kind is SubjectKind.BYPRODUCT:
        molecules = [m for m in step.byproducts if structure_key(m) == subject.core]
        hazard = molecule_hazards(molecules[0])
    else:
        ops = step.envelope.procedure.operations
        if subject.kind is SubjectKind.USE_STREAM:
            use = next(o for o in ops if o.ordinal == subject.ordinal).material_uses[subject.index]
        else:
            use = next(u for o in ops for u in o.material_uses if u.identity is not None
                       and structure_key(u.identity) == subject.core)
        hazard = molecule_hazards(use.identity) if use.identity is not None else hazards_for_named(use.name)
    return () if hazard is None else tuple(hazard.ghs_codes)


def test_c1_2_routed_aqueous_neutral_is_never_sufficient_for_a_species_with_ghs_codes():
    """Exhaustive over every species-bearing subject of three fixtures: ROUTED(AQUEOUS_NEUTRAL) on a subject whose species
    carries non-empty GHS codes always leaves HAZARDOUS among the derived categories. Pre-S18 FAILS on the methanol
    residual (dme) and the methanol wash stream."""
    fixtures = (_dme(), _micro(_op(uses=(_use("methanol", ProcedureMaterialRole.WASH, _METHANOL),
                                         _use("brine", ProcedureMaterialRole.WASH)))),
                _micro(_op(uses=(_use("sulfuric acid", ProcedureMaterialRole.CATALYST, _H2SO4),))))
    hazardous_checked = 0
    for route in fixtures:
        for subject in stream_subjects(route.steps[0]):
            if subject.kind is SubjectKind.OP_STREAM:
                continue  # the declared boundary: no species, the category is the only evidence
            try:
                routed = _with(route, _d(subject))
            except (StepError, ValueError):
                continue
            if _species_codes(route, subject):
                assert _HAZ in derive_waste(routed)[0], subject.label
                hazardous_checked += 1
    assert hazardous_checked >= 5  # methanol x3 (dme residual, micro residuals), acetic acid x2, the wash, H2SO4


def test_c1_2_one_mapping_empty_record_implies_nothing():
    assert _hazard_categories(()) == frozenset()
    assert _hazard_categories(("H225",)) == frozenset({_HAZ})


# =====================================================================================================================
# C1-3 -- a case-only name match is POSSIBLE at most: never certifying, never a cover, never a merge
# =====================================================================================================================

def _named_bottle(key: str, *, mid="bottle", phase=Phase.SOLID) -> StockMaterial:
    ev = IntervalEvidence.build(kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
                                inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                                        TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
                                domain_of_validity="fixture: the bench declares this bottle pure")
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, (MaterialComponent.evidenced(key, "active", ev),), phase,
                         "fixture", quantity=StockQuantity.of("5", "g"), phase_evidence=EvidenceKind.USER_DECLARED)


def _name_req(name: str) -> MaterialRequirement:
    return MaterialRequirement(identity=None, phase=None, quantity=QuantityDemand.combine((StockQuantity.of("1", "g"),)),
                               role="procedure material (REACTANT)", evidence_source="fixture", name=name,
                               specification=MaterialSpecification())


def test_c1_3_the_two_folds_have_one_owner_and_differ_only_by_case():
    assert collapse_material_name("  CO \t gas ") == "CO gas"
    assert normalize_material_name("  CO \t gas ") == "co gas" == collapse_material_name("  CO \t gas ").casefold()
    assert collapse_material_name("CO") != collapse_material_name("Co")
    assert normalize_material_name("CO") == normalize_material_name("Co")  # the lossy fold, by design only POSSIBLE


def test_c1_3_stock_case_exact_matching():
    cobalt = _named_bottle("Co")
    assert cobalt.active_fraction_interval("CO", case_exact=True) is None
    assert cobalt.active_fraction_interval("CO") is not None            # the possibility fold still sees it
    assert cobalt.spec_view("CO", case_exact=True) is None
    assert cobalt.active_fraction_interval(" Co ", case_exact=True) is not None  # whitespace is spelling


def test_c1_3_a_case_only_bottle_is_a_possible_source_never_a_certifying_edge():
    """Pre-S18 FAILS: the "Co" (cobalt) bottle was a FIT, commensurable edge for a "CO" demand."""
    edge = _edge(_name_req("CO"), _named_bottle("Co"))
    assert edge is not None and edge.status is CapabilityStatus.UNKNOWN and not edge.commensurable
    assert "case-folding" in edge.note


def test_c1_3_an_exact_or_whitespace_variant_spelling_still_certifies():
    for key in ("CO", "  CO "):
        edge = _edge(_name_req("CO"), _named_bottle(key))
        assert edge is not None and edge.status is CapabilityStatus.FIT and edge.commensurable, key


def test_c1_3_a_case_only_bottle_is_not_proof_of_absence_either():
    from smartchem.capability.assess import _material_axis

    axis = _material_axis((_name_req("CO"),), (_named_bottle("Co"),))
    assert axis.status is CapabilityStatus.UNKNOWN, axis.reasons


def _r2(metal: str) -> ExperimentRoute:
    """Wave C1 r2: op #1 names ("methanol", "CO", ``metal``); typed uses methanol + a name-only REACTANT "CO"."""
    base = _dme()
    ops = list(base.steps[0].envelope.procedure.operations)
    gas = ProcedureMaterialUse(name="CO", role=ProcedureMaterialRole.REACTANT, identity=None,
                               quantity=StockQuantity.of("1", "g"), evidence_source=_URL)
    ops[0] = dc.replace(ops[0], materials=("methanol", "CO", metal), material_uses=ops[0].material_uses + (gas,))
    return _rendered(base, ops)


def test_c1_3_r2_a_raw_co_string_is_never_covered_by_a_typed_co_and_never_vanishes():
    """Pre-S18 FAILS: the typed "CO" covered the raw "Co", which then appeared in no material requirement, no waste
    obligation and no containment line -- and the material axis read FIT off the cobalt bottle."""
    route = _r2("Co")
    reqs = compile_capability_requirements(route)
    untyped = [m for m in reqs.material if m.untyped_source_text]
    assert [m.name for m in untyped] == ["Co"]
    assert any("introduces untyped material 'Co'" in u for u in derive_waste(route)[2])
    assert any("'Co'" in line for line in reqs.hazard_unresolved)
    profile = dc.replace(_exact_profile(), material_inventory=(_pure("methanol-pure", _METHANOL), _named_bottle("Co")))
    a = _assess(route, profile)
    assert a.material.status is CapabilityStatus.UNKNOWN and not a.is_capability_fit


def test_c1_3_two_name_only_uses_differing_by_case_are_two_demands_and_two_obligations():
    """"CO" and "Co" as two name-only REACTANT uses: two material requirements (a fold merged them into one demand one
    bottle then certified for both), two RESIDUAL subjects (the name half of a subject key never folds case) and two
    residual obligations -- a statement about "CO" settles "CO" and leaves "Co" open."""
    uses = tuple(ProcedureMaterialUse(name=n, role=ProcedureMaterialRole.REACTANT, identity=None,
                                      quantity=StockQuantity.of("1", "g"), evidence_source=_URL) for n in ("CO", "Co"))
    route = _micro(_op(uses=uses), _op(OperationKind.FILTER))
    names = sorted(m.name for m in compile_capability_requirements(route).material if m.identity is None)
    assert names == ["CO", "Co"]
    residuals = [u for u in derive_waste(route)[2] if "unreacted/excess" in u and ("'CO'" in u or "'Co'" in u)]
    assert len(residuals) == 2, residuals
    gas = _subject_of(route, SubjectKind.RESIDUAL, core="name:CO")
    assert _subject_of(route, SubjectKind.RESIDUAL, core="name:Co") != gas
    # the statement lands on "CO" alone (and L3 refuses it there: no hazard record answers to the name "CO")
    _c, _r, unresolved = derive_waste(_with(route, _d(gas, category=_HAZ)))
    refusals = [u for u in unresolved if "discharges nothing" in u]
    assert len(refusals) == 1 and "residual 'CO'" in refusals[0], refusals


# =====================================================================================================================
# C1-4 -- RECOVERED needs structural corroboration: order, a certified phase, a phase the op can recover
# =====================================================================================================================

def test_c1_4_r5_a_gravity_filter_does_not_recover_a_liquid_residual():
    """Pre-S18 FAILS: RECOVERED(methanol) via the witness's name-less FILTER op discharged it; the route was FIT."""
    water, op3, methanol = _dme_subjects()
    route = _with(_dme(), _d(water), _d(op3), _d(methanol, _RECOVERED, via_op=3))
    _c, reasons, unresolved = derive_waste(route)
    assert any("FILTER operation cannot recover a LIQUID subject" in u for u in unresolved), unresolved
    assert not any("residual 'methanol'" in r and "(S10)" in r for r in reasons)
    assert not _assess(route).is_capability_fit


def test_c1_4_liveness_a_still_after_the_charge_recovers_the_liquid():
    route = _micro(_op(OperationKind.DISTILL))
    methanol = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_METHANOL))
    _c, reasons, unresolved = derive_waste(_with(route, _d(methanol, _RECOVERED, via_op=2)))
    assert any("residual 'methanol'" in r and "RECOVERED via op #2" in r for r in reasons)
    assert not any("'methanol' (SUBSTRATE)" in u for u in unresolved)


def test_c1_4_a_recovery_before_the_charge_recovers_nothing():
    """The still (op #1) precedes the op that charges methanol (op #2). Pre-S18 FAILS (it discharged)."""
    base_uses = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL),
                 _use("acetic acid", ProcedureMaterialRole.REACTANT, _ACETIC))
    ops = (dc.replace(_op(OperationKind.DISTILL), ordinal=1),
           dc.replace(_op(role=OperationRole.REACTION, uses=base_uses), ordinal=2))
    route = ExperimentRoute(ROUTE_SCHEMA, (_sourced_step((_ACETIC, _METHANOL), (_MEOAC, _WATER), _MEOAC, ops),))
    methanol = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_METHANOL))
    _c, _r, unresolved = derive_waste(_with(route, _d(methanol, _RECOVERED, via_op=1)))
    assert any("does not come after op #2" in u for u in unresolved), unresolved


@pytest.mark.parametrize("phase", [None, PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED)],
                         ids=["no-phase", "author-inferred"])
def test_c1_4_an_uncertified_phase_can_be_recovered_by_nothing(phase):
    use = dc.replace(_use("catalyst x", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT), phase=phase)
    route = _micro(_op(uses=(use,)), _op(OperationKind.DISTILL))
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_UNRECORDED_CAT))
    _c, _r, unresolved = derive_waste(_with(route, _d(residual, _RECOVERED, via_op=3)))
    assert any("phase is not CERTIFIED" in u for u in unresolved), unresolved


def test_c1_4_a_filter_recovers_a_certified_solid():
    use = dc.replace(_use("catalyst x", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT), phase=_SQ_SOLID)
    route = _micro(_op(uses=(use,)), _op(OperationKind.FILTER))
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_UNRECORDED_CAT))
    _c, reasons, _u = derive_waste(_with(route, _d(residual, _RECOVERED, via_op=3)))
    assert any("catalyst residual 'catalyst x'" in r and "(S10)" in r for r in reasons)


def test_c1_4_a_use_stream_recovery_obeys_the_same_phase_law():
    route = _micro(_op(uses=(_use("brine", ProcedureMaterialRole.WASH),)), _op(OperationKind.FILTER),
                   _op(OperationKind.SEPARATE))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    assert any("cannot recover a LIQUID" in u for u in derive_waste(_with(route, _d(stream, _RECOVERED, via_op=3)))[2])
    assert not any("spent workup stream 'brine'" in u
                   for u in derive_waste(_with(route, _d(stream, _RECOVERED, via_op=4)))[2])


def test_c1_4_the_phase_table_covers_exactly_the_recovery_op_kinds():
    assert frozenset(_RECOVERABLE_PHASES) == RECOVERY_OP_KINDS
    assert all(Phase.GAS not in phases for phases in _RECOVERABLE_PHASES.values())


# =====================================================================================================================
# the witness is untouched, and the monotonicity principle as a property
# =====================================================================================================================

def test_the_synthetic_witness_still_reaches_capability_fit_under_the_exact_bench():
    route = _with(_dme(), *_witness_dispositions())
    cats, _r, unresolved = derive_waste(route)
    assert cats == frozenset({_AN}) and unresolved == ()  # water is benign; the op #3 stream names no species
    a = _assess(route)
    assert _statuses(a) == _WITNESS_TABLE and a.is_capability_fit


def _dispositions_for(route: ExperimentRoute):
    """Every structurally-legal single disposition on ``route``'s step: each subject x each value x (each category |
    each recovery-op ordinal)."""
    ops = route.steps[0].envelope.procedure.operations
    recovery = [op.ordinal for op in ops if op.kind in RECOVERY_OP_KINDS]
    for subject in stream_subjects(route.steps[0]):
        for category in WasteCapability:
            yield _d(subject, category=category)
        if subject.kind is SubjectKind.RESIDUAL:
            yield _d(subject, _CC)
        if subject.kind in (SubjectKind.RESIDUAL, SubjectKind.USE_STREAM):
            for ordinal in recovery:
                yield _d(subject, _RECOVERED, via_op=ordinal)


def _added(route: ExperimentRoute, disposition) -> "ExperimentRoute | None":
    current = route.steps[0].envelope.procedure.stream_dispositions
    if any(d.subject == disposition.subject for d in current):
        return None
    try:
        return _with(route, *current, disposition)
    except (StepError, ValueError):
        return None  # refused at binding (e.g. CONSUMED_COMPLETELY on a species the step does not net-consume)


_BENCHES = (frozenset({_AN}), frozenset({_AN, _HAZ}), frozenset({_HAZ}))


def _monotone(base: ExperimentRoute, grown: ExperimentRoute, profile_of) -> None:
    before, after = derive_waste(base)[0], derive_waste(grown)[0]
    assert before <= after, (sorted(c.value for c in before), sorted(c.value for c in after))
    for waste in _BENCHES:
        if _assess(base, profile_of(waste)).overall is CapabilityStatus.BLOCKED:
            assert not _assess(grown, profile_of(waste)).is_capability_fit, waste


_BASES = {
    "witness-minus-one": lambda: _with(_dme(), *_witness_dispositions()[:2]),
    # the r6 route with only two of its four statements, so every other subject is free to receive one
    "r6-typed-h2so4": lambda: _with(_r6(()), *_r6(()).steps[0].envelope.procedure.stream_dispositions[:2]),
    "r1-routed-methanol-minus-water": lambda: _with(_dme(), *(_d(s) for s in _dme_subjects()[1:])),
}


@pytest.mark.parametrize("base_name", sorted(_BASES))
def test_monotone_adding_any_disposition_never_removes_a_category_nor_turns_blocked_into_fit(base_name):
    base = _BASES[base_name]()
    profile_of = _r6_profile if base_name.startswith("r6") else _exact_profile
    grown_count = 0
    for disposition in _dispositions_for(base):
        grown = _added(base, disposition)
        if grown is None:
            continue
        _monotone(base, grown, profile_of)
        grown_count += 1
    assert grown_count >= 1


_EVIDENCE_STRINGS = ("sulfuric acid", "Sulfuric acid", " sulfuric  acid ", "SULFURIC ACID", "catalyst x", "H2SO4",
                     "Catalyst X")


@pytest.mark.parametrize("extra", _EVIDENCE_STRINGS, ids=repr)
def test_monotone_adding_an_envelope_catalyst_string_never_removes_a_category_nor_turns_blocked_into_fit(extra):
    """Pre-S18 FAILS on every non-exact sulfuric-acid spelling (it removed HAZARDOUS and turned BLOCKED into FIT)."""
    base = _r6(())
    grown = _r6((extra,))
    _monotone(base, grown, _r6_profile)


@pytest.mark.parametrize("extra", [("sulfuric acid", _H2SO4), ("Sulfuric acid", _H2SO4), ("catalyst x", _UNRECORDED_CAT),
                                   ("acid catalyst", _UNRECORDED_CAT), ("brine", None)],
                         ids=lambda x: x[0])
def test_monotone_adding_a_typed_catalyst_use_never_removes_a_category(extra):
    name, identity = extra
    base = _micro(_op(uses=(_use("sulfuric acid", ProcedureMaterialRole.CATALYST, _H2SO4),)),
                  catalysts=("Sulfuric acid",))
    grown = _micro(_op(uses=(_use("sulfuric acid", ProcedureMaterialRole.CATALYST, _H2SO4),
                             _use(name, ProcedureMaterialRole.CATALYST, identity))),
                   catalysts=("Sulfuric acid",))
    assert derive_waste(base)[0] <= derive_waste(grown)[0]


def test_monotone_every_pair_of_witness_dispositions_is_a_subset_chain():
    """Along every order of adding the witness's three dispositions, the category set only grows."""
    for order in itertools.permutations(_witness_dispositions()):
        seen: "frozenset[WasteCapability]" = frozenset()
        for k in range(len(order) + 1):
            cats = derive_waste(_with(_dme(), *order[:k]) if k else _dme())[0]
            assert seen <= cats
            seen = cats


# =====================================================================================================================
# Wave C5 folded in: F1 (fold-name dedup), F3 (twin-core rebind), F4 (rinse covers a reactant), F5, F6 (name borrows L3)
# =====================================================================================================================

@pytest.mark.parametrize("second", ["Catalyst", "catalyst"])
def test_c5_f1_a_second_catalyst_species_under_a_fold_equal_name_keeps_its_obligation(second):
    """Pre-S18 FAILS: the tert-butylbenzene residual never existed (``catalyst_seen`` keyed by folded name), so no
    disposition could ever be asked about it and the waste axis read FIT."""
    route = _micro(_op(uses=(_use("catalyst", ProcedureMaterialRole.CATALYST, _H2SO4),
                             _use(second, ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT))), _op(OperationKind.FILTER))
    cats, _r, unresolved = derive_waste(route)
    assert _HAZ in cats
    assert any(f"catalyst residual {second!r}" in u and "no hazard record" in u for u in unresolved), unresolved


def test_c5_f3_twin_filters_swapped_make_the_subject_vanish_never_rebind():
    """Gravity vs vacuum filtration: identical kind/role/uses/materials, different apparatus. Pre-S18 FAILS: the
    subject sets were identical after the swap and op #3's statement discharged the OTHER filter."""
    gravity = dc.replace(_op(OperationKind.FILTER), apparatus=("fluted filter paper",))
    vacuum = dc.replace(_op(OperationKind.FILTER), apparatus=("Buchner funnel", "vacuum"))
    a, b = _micro(_op(), gravity, vacuum), _micro(_op(), vacuum, gravity)
    assert stream_subjects(a.steps[0]) != stream_subjects(b.steps[0])
    op3 = _subject_of(a, SubjectKind.OP_STREAM, ordinal=3)
    with pytest.raises(StepError, match="does not exist in this step"):
        _with(b, _d(op3))


@pytest.mark.parametrize("field,value", [
    ("formulation", "hot conc. 12 M HCl(aq) rinse"),
    ("quantity", StockQuantity.of("250", "mL")),
    ("phase", _SQ_SOLID),
], ids=["formulation", "quantity", "phase"])
def test_c5_f3_a_typed_rewrite_of_a_use_unbinds_its_disposition(field, value):
    """Pre-S18 FAILS: ``use_core`` was (role, species) only, so the rewritten rinse kept the disposition written for
    the cold-water one."""
    original = _use("cold water", ProcedureMaterialRole.RINSE)
    before, after = _micro(_op(uses=(original,))), _micro(_op(uses=(dc.replace(original, **{field: value}),)))
    subject = _subject_of(before, SubjectKind.USE_STREAM)
    assert subject not in stream_subjects(after.steps[0])
    with pytest.raises(StepError, match="does not exist in this step"):
        _with(after, _d(subject))


def test_c5_f3_presentation_edits_never_unbind():
    """The other half of the law: a locator or a structure-bearing use's display name is presentation."""
    use = _use("methanol", ProcedureMaterialRole.WASH, _METHANOL)
    base = _micro(_op(uses=(use,)))
    subject = _subject_of(base, SubjectKind.USE_STREAM)
    reworded = _micro(dc.replace(_op(uses=(dc.replace(use, name="MeOH", evidence_source="elsewhere"),)),
                                 locator="https://example.test/another-locator"))
    assert subject in stream_subjects(reworded.steps[0])


def test_c5_f4_a_reactant_typed_only_as_a_rinse_keeps_its_residual_obligation():
    """Pre-S18 FAILS: the rinse use's identity marked acetic acid 'covered', so its residual was never minted and one
    ROUTED on the rinse stream closed the reactant's whole waste question."""
    route = _micro(base_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL),
                              _use("acetic acid", ProcedureMaterialRole.RINSE, _ACETIC)))
    marker = "typed only in a non-stoichiometric role"
    assert any(marker in u and repr(_ACETIC) in u for u in derive_waste(route)[2])
    rinse = _subject_of(route, SubjectKind.USE_STREAM)
    _c, _r, unresolved = derive_waste(_with(route, _d(rinse)))
    assert any(marker in u and repr(_ACETIC) in u for u in unresolved)


def test_c5_f5_a_recovery_before_the_stream_exists_recovers_nothing():
    """op #2 FILTER precedes the op #3 brine wash. Pre-S18 FAILS (it discharged the brine stream)."""
    route = _micro(_op(OperationKind.SEPARATE), _op(uses=(_use("brine", ProcedureMaterialRole.WASH),)))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    _c, _r, unresolved = derive_waste(_with(route, _d(stream, _RECOVERED, via_op=2)))
    assert any("does not come after op #3" in u for u in unresolved), unresolved
    assert any("spent workup stream 'brine'" in u and "F49" in u for u in unresolved)


def test_c5_f6_an_identity_never_borrows_the_record_of_its_display_name():
    """tert-butylbenzene labelled "water": pre-S18 FAILS -- the empty water record passed L3 and ROUTED discharged it."""
    route = _micro(_op(uses=(_use("water", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),)))
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_UNRECORDED_CAT))
    _c, _r, unresolved = derive_waste(_with(route, _d(residual)))
    assert any("no hazard record" in u and "(L3)" in u for u in unresolved), unresolved
    assert any("catalyst residual 'water'" in u and "not consumed (no hazard record)" in u for u in unresolved)


# =====================================================================================================================
# S18 residual (parent, integration) -- the containment scan never CLEARS a typed structure by its display name, and no
# name-keyed lookup table carries a key whose case variants denote two different formulas
# =====================================================================================================================

def test_s18r_containment_never_clears_a_typed_structure_by_its_display_name():
    """tert-butylbenzene labelled "water" (C5-F6's disease, containment leg). Pre-fix FAILS: the structure has no hazard
    record, so ``_hazard_scan`` fell back to the NAME and the empty water record cleared it -- no containment reason, no
    unresolved line, a silent pass on an unknown species."""
    route = _micro(_op(uses=(_use("water", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),)))
    reqs = compile_capability_requirements(route)
    assert any("procedure-only 'water'" in line and "no GHS record" in line for line in reqs.hazard_unresolved), (
        reqs.hazard_unresolved)
    assert not _assess(route, _maximal_profile((_pure("methanol-pure", _METHANOL),))).is_capability_fit


def test_s18r_a_display_name_with_ghs_codes_may_still_force_containment():
    """The one-sided rule: a name record is not bound to the typed structure, so it may FORCE containment (the safe
    direction -- a demand the bench can only over-satisfy) but never clear it."""
    route = _micro(_op(uses=(_use("carbon monoxide", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),)))
    reqs = compile_capability_requirements(route)
    assert any("'carbon monoxide'" in r and "H331" in r for r in reqs.containment_reasons), reqs.containment_reasons


def _case_variant_formulas(key: str) -> "set[tuple]":
    """Every distinct formula a case variant of ``key`` parses to (``key`` letters/digits only)."""
    from smartchem.formula_expr import FormulaSyntaxError, parse_formula_expr

    letters = [i for i, ch in enumerate(key) if ch.isalpha()]
    out = set()
    for mask in range(1 << len(letters)):
        chars = list(key)
        for bit, i in enumerate(letters):
            chars[i] = chars[i].upper() if mask >> bit & 1 else chars[i].lower()
        try:
            out.add(tuple(sorted(parse_formula_expr("".join(chars)).to_formula().counts)))
        except (FormulaSyntaxError, ValueError):
            continue
    return out


def test_s18r_no_case_folded_lookup_key_names_two_formulas():
    """``hazards_for_named`` and ``catalyst_availability`` fold case before the lookup. A fold is sound only on a key
    that is not a case-sensitive token (``co`` would answer for both CO and Co). Pin it: no hazard-record name has two
    case-variant formulas, and every catalyst-table key that does sits in the exact-spelling ledger, whose spelling is
    the key's own and parses to exactly one formula."""
    import re

    import smartchem.experiment.catalyst_availability as ca
    from smartchem.formula_expr import parse_formula_expr

    def ambiguous(keys):
        return {k for k in keys if re.fullmatch(r"[a-z0-9]{1,10}", k) and len(_case_variant_formulas(k)) > 1}

    assert not ambiguous({ref.name for ref in HAZARD_REFS})
    catalyst_keys = set(ca._COMMODITY_BY_NAME) | set(ca._CATALYST_TABLE)
    # 0.9.5 A15 (Wave D F10): the ledger is now the honest spelling of EVERY formula-token key -- a superset of the
    # two-reading ones, multi-word keys included -- and the case rule runs on every key, ledger or not. The exhaustive
    # case-variant invariant lives in tests/test_v0_9_5_wave_d_capability.py.
    assert ambiguous(catalyst_keys) <= set(ca._CASE_EXACT_SPELLING)
    for key, spelling in ca._CASE_EXACT_SPELLING.items():
        assert spelling.casefold() == key
        parsed = 0
        for token in spelling.split():
            try:
                parse_formula_expr(token)
                parsed += 1
            except ValueError:  # FormulaSyntaxError is a ValueError
                continue
        assert parsed, spelling  # every entry spells at least one formula token
    # the instrument discriminates: a collision key IS caught, a plain one is not
    assert len(_case_variant_formulas("co")) == 2 and len(_case_variant_formulas("hcl")) == 1


@pytest.mark.parametrize("spelling, tier", [("Na2CO3", "GROCERY"), (" Na2CO3 ", "GROCERY"), ("Na2Co3", None),
                                            ("na2co3", None), ("K2CO3", "HARDWARE"), ("K2Co3", None),
                                            ("NaHCo3", None), ("PtO2", "INDUSTRIAL"), ("PTO2", None),
                                            ("HCl", "HARDWARE"), ("hcl", "HARDWARE")])
def test_s18r_a_case_ambiguous_catalyst_key_matches_only_its_exact_spelling(spelling, tier):
    """Pre-fix FAILS on the cobalt spellings: ``Na2Co3`` read as GROCERY-tier sodium carbonate (a kitchen VOUCH for a
    cobalt formula)."""
    from smartchem.experiment.catalyst_availability import catalyst_availability

    got = catalyst_availability(spelling)
    assert (None if got is None else got.name) == tier


def test_s18r_two_catalysts_differing_by_case_are_two_procurement_rows():
    """Pre-fix FAILS: the case-folded procurement dedup kept ``Na2CO3`` (GROCERY) and dropped ``Na2Co3`` (unrecognized),
    so the cobalt spelling vanished from the procurement axis."""
    route = _micro(catalysts=("Na2CO3", "Na2Co3"))
    rows = compile_capability_requirements(route).procurement_catalysts
    assert [name for name, _tier in rows] == ["Na2CO3", "Na2Co3"], rows
    assert rows[1][1] is None
