"""Round V X-high continuation -- the capability-core regressions (barrier D14-D18, §7.2 of the Round V audit).

**One discriminating test per reproduced hole, each on an AXIS in isolation.** The corpus has no CAPABILITY_FIT, and
that universal UNKNOWN can mask a per-axis false FIT ("overall stayed UNKNOWN anyway" is not evidence). So every test
below builds a real, conserving micro route whose OTHER axes are deliberately clean against a fully-declared bench,
proves the axis under test would be FIT/NA on the clean control, and then shows the reproduced shape can no longer
certify it. Every expectation failed on the Round-V WIP (`78554a2`) -- they are the Wave A' reproducers, pinned.
"""
from __future__ import annotations

import dataclasses as dc

import pytest

from smartchem.capability import assess, compile_capability_requirements
from smartchem.capability.assess import CAPABILITY_ASSESSMENT_SCHEMA, AxisResult, CapabilityAssessment
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    WasteCapability,
)
from smartchem.capability.presets import custom
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.contracts import EvidenceStatus
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.data.reagents import Availability
from smartchem.experiment.readiness import evaluate_route
from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
)
from smartchem.material_spec import ConcentrationBasis, EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements
from smartchem.smiles import parse_smiles

S = CapabilityStatus
PASSES = (S.FIT, S.NOT_APPLICABLE, S.UNCONSTRAINED)

_AC, _ME, _MEOAC, _WATER, _AC2O = (parse_smiles(x) for x in ("CC(=O)O", "CO", "CC(=O)OC", "O", "CC(=O)OC(C)=O"))
_SQ, _AI, _UD, _UNK = (EvidenceKind.SOURCE_QUOTED, EvidenceKind.AUTHOR_INFERRED, EvidenceKind.USER_DECLARED,
                       EvidenceKind.UNKNOWN)
_U = EvidenceField.unknown()


def _pf(value, loc="fixture"):
    return EvidenceField.present(value, loc)


def _use(name, role, identity=None, qty="10", *, phase=Phase.LIQUID, ev=_SQ, unit="mL"):
    return ProcedureMaterialUse(
        name=name, role=role, identity=identity,
        phase=None if phase is None else PhaseClaim(phase, ev),
        quantity=None if qty is None else StockQuantity.of(qty, unit), evidence_source="fixture micro-route")


_BASE_USES = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _ME),
              _use("acetic acid", ProcedureMaterialRole.REACTANT, _AC))

#: a fully-declared, internally consistent whole-step process record (the clean process world).
_CLEAN_RECORD = ProcessRequirements(
    workup_included=True, provenance="fixture: fully declared step",
    elapsed_minutes=Interval(0, 120, "min"), active_minutes=Interval(0, 30, "min"),
    attention=Attention.PASSIVE, agitation=Agitation.NONE,
    peak_temperature_k=298.15, min_pressure_atm=1.0, max_pressure_atm=1.0)


def _op(kind, role=OperationRole.OTHER, **kw) -> ProcedureOperation:
    return ProcedureOperation(ordinal=1, kind=kind, role=role, locator="fixture", **kw)


def _procedure(ops) -> ProcedureEvidence:
    return ProcedureEvidence(reaction_scope="fixture micro-route", source=None, scale=_U, operations=tuple(ops),
                             quench=_U, workup_isolation=_U, separation=_U, wash=_U, drying=_U, purification=_U,
                             analytical_verification=_U)


def _envelope(ops=(), *, uses=_BASE_USES, process=_CLEAN_RECORD, procedure=True, **env) -> ConditionEnvelope:
    op1 = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                             material_uses=tuple(uses), locator="fixture")
    ordered = [op1] + [dc.replace(op, ordinal=i) for i, op in enumerate(ops, start=2)]
    env.setdefault("temperature", Interval(298.15, 298.15, "K"))
    env.setdefault("pressure", Interval(1.0, 1.0, "atm"))
    if any(env.get(k) for k in ("temperature", "pressure", "duration", "medium", "catalysts", "applied_field")):
        env.setdefault("status", EvidenceStatus.EXPERIMENTAL)
        env.setdefault("provenance", "fixture micro-route: declared conditions (not a sourced citation)")
    return ConditionEnvelope(procedure=_procedure(ordered) if procedure else None, process=process, **env)


def _route(*ops, **kw) -> ExperimentRoute:
    """AcOH + MeOH -> MeOAc + H2O: a real conserving step, both inputs typed (identity + certified phase + quantity)."""
    step = ExperimentStep(STEP_SCHEMA, _MEOAC, (_AC, _ME), (_MEOAC, _WATER), (), _envelope(ops, **kw))
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


def _evidence(lo="1", hi="1", *, kernel=DerivationKernel.USER_DECLARED_V1, kind=_UD, unit=InputUnit.FRACTION,
              floor=None) -> IntervalEvidence:
    loc = "https://example.test/spec" if kind in (_SQ, EvidenceKind.DERIVED, EvidenceKind.CLAMPED) else ""
    if floor is not None:
        return IntervalEvidence.build(kernel=kernel, basis=ConcentrationBasis.MASS_FRACTION,
                                      inputs=(TypedInput("floor", floor, unit, kind, loc),),
                                      source_locators=(loc,), domain_of_validity="fixture")
    return IntervalEvidence.build(kernel=kernel, basis=ConcentrationBasis.MASS_FRACTION,
                                  inputs=(TypedInput("low", lo, unit, kind, loc), TypedInput("high", hi, unit, kind, loc)),
                                  source_locators=(loc,) if loc else (), domain_of_validity="fixture")


def _bottle(mid, key, *, phase=Phase.LIQUID, phase_ev=_UD, evidence=None, qty="500") -> StockMaterial:
    comp = MaterialComponent.evidenced(key, "active", evidence if evidence is not None else _evidence())
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, (comp,), phase, "fixture: operator-declared bottle",
                         quantity=StockQuantity.of(qty, "mL"), phase_evidence=phase_ev)


_FULL_BOUNDS = ProcessBounds.of(
    max_step_minutes=600.0, max_total_minutes=600.0, max_active_minutes=120.0,
    allowed_attention=tuple(Attention), min_check_interval_minutes=1.0, allowed_agitation=tuple(Agitation))


def _bench(*extra, **over):
    """A fully-declared custom bench: every axis declared, every bound finite, budget NO_LIMIT (a tagged preference)."""
    base = dict(
        profile_id="xhigh-clean-bench",
        material_inventory=(_bottle("methanol-pure", _ME), _bottle("acetic-pure", _AC)) + tuple(extra),
        equipment=frozenset(EquipmentCapability),
        physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, min_temperature_k=250.0,
                                          min_pressure_atm=0.5, max_pressure_atm=2.0),
        process_bounds=_FULL_BOUNDS,
        containment=frozenset(ContainmentCapability), measurement=frozenset(MeasurementMethod),
        waste_handling=frozenset(WasteCapability), procurement=frozenset(Availability),
        no_limit_dimensions=frozenset({"budget"}),
    )
    base.update(over)
    return custom(**base)


def _assess(route, profile=None):
    return assess(_bench() if profile is None else profile, compile_capability_requirements(route),
                  evaluate_route(route))


# ---------------------------------------------------------------------------------------------------------------
# the clean control: every axis this file isolates is a PASS on the clean world (so each test below is discriminating)
# ---------------------------------------------------------------------------------------------------------------

def test_the_clean_micro_world_passes_every_axis_this_file_isolates():
    a = _assess(_route())
    assert a.material.status is S.FIT, a.material.reasons
    assert a.physical.status is S.FIT, a.physical.reasons
    assert a.process.status is S.FIT, a.process.reasons
    assert a.equipment.status is S.NOT_APPLICABLE
    assert a.measurement.status is S.NOT_APPLICABLE


# ---------------------------------------------------------------------------------------------------------------
# D14 -- the physical RANGE (F-1, F-10, P4, P5)
# ---------------------------------------------------------------------------------------------------------------

_COOL_77 = _op(OperationKind.COOL, apparatus=("ice bath",), temperature=_pf(Interval(77, 77, "K")))


def test_f1_a_77_k_cooling_demand_is_read_and_blocks_against_the_bench_floor():
    reqs = compile_capability_requirements(_route(_COOL_77))
    assert reqs.physical.min_temperature_k == 77 and reqs.physical.max_temperature_k == 298.15
    assert _assess(_route(_COOL_77)).physical.status is S.BLOCKED


def test_f1_a_real_low_demand_against_an_undeclared_floor_is_unknown_never_fit():
    bench = _bench(physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, min_pressure_atm=0.5,
                                                     max_pressure_atm=2.0))
    assert _assess(_route(_COOL_77), bench).physical.status is S.UNKNOWN


def test_f1_the_lowest_statement_wins_the_low_side():
    warm = _op(OperationKind.HOLD, apparatus=("hot plate",), temperature=_pf(Interval(373.15, 373.15, "K")))
    cold = _op(OperationKind.COOL, apparatus=("ice bath",), temperature=_pf(Interval(273.15, 273.15, "K")))
    reqs = compile_capability_requirements(_route(warm, cold))
    assert (reqs.physical.min_temperature_k, reqs.physical.max_temperature_k) == (273.15, 373.15)
    assert _assess(_route(warm, cold), _bench(physical_bounds=PhysicalBounds.of(
        max_temperature_k=500.0, min_temperature_k=300.0, min_pressure_atm=0.5,
        max_pressure_atm=2.0))).physical.status is S.BLOCKED


@pytest.mark.parametrize("field, text", [("temperature", "650 C tube furnace"), ("pressure", "50 atm autoclave")])
def test_f10_prose_is_never_covered_by_an_unrelated_process_extremum(field, text):
    op = _op(OperationKind.HOLD, apparatus=("hot plate",), **{field: _pf(text)})
    reqs = compile_capability_requirements(_route(op))
    assert any("only in prose" in u and text in u for u in reqs.physical_unresolved), reqs.physical_unresolved
    assert _assess(_route(op)).physical.status is S.UNKNOWN


def test_p4_a_thermal_op_with_no_temperature_is_not_masked_by_an_unrelated_lower_statement():
    record = dc.replace(_CLEAN_RECORD, peak_temperature_k=None)
    still = _op(OperationKind.DISTILL, apparatus=("simple distillation apparatus",))
    route = _route(still, process=record)
    assert any("D14 ii" in u for u in compile_capability_requirements(route).physical_unresolved)
    assert _assess(route).physical.status is S.UNKNOWN
    # ... and the whole-step peak (the record's own whole-step contract) IS a legitimate cover for the high side:
    assert _assess(_route(still)).physical.status is S.FIT


def test_p5_an_envelope_temperature_does_not_mask_a_heat_op_on_a_step_with_no_process_record():
    heat = _op(OperationKind.HEAT, apparatus=("hot plate",))
    route = _route(heat, process=None)
    assert any("D14 ii" in u for u in compile_capability_requirements(route).physical_unresolved)
    assert _assess(route).physical.status is S.UNKNOWN


def test_d14_iii_a_cool_op_with_no_typed_temperature_leaves_the_low_side_unread():
    cool = _op(OperationKind.COOL, apparatus=("ice bath",))
    assert any("D14 iii" in u for u in compile_capability_requirements(_route(cool)).physical_unresolved)
    assert _assess(_route(cool)).physical.status is S.UNKNOWN


def test_d14_iv_a_step_with_no_procedure_evidence_has_an_unread_low_side():
    route = _route(procedure=False)
    reqs = compile_capability_requirements(route)
    assert any("no ProcedureEvidence" in u and "LOW" in u for u in reqs.physical_unresolved)
    assert not any("HIGH" in u for u in reqs.physical_unresolved)  # the process peak covers the high side
    assert _assess(route).physical.status is S.UNKNOWN


# ---------------------------------------------------------------------------------------------------------------
# D15 -- the ordered TIMELINE and an independently-correct process axis (F-2, F-3, F-8)
# ---------------------------------------------------------------------------------------------------------------

def _hold(minutes=None, prose=None):
    kw = {}
    if minutes is not None:
        kw["duration"] = _pf(Interval(minutes, minutes, "min"))
    if prose is not None:
        kw["duration"] = _pf(prose)
    return _op(OperationKind.HOLD, apparatus=("hot plate",), temperature=_pf(Interval(298.15, 298.15, "K")), **kw)


def test_f2_a_prose_duration_is_an_unread_time_demand():
    route = _route(_hold(prose="3 weeks"))
    assert any("3 weeks" in u and "F-2" in u for u in compile_capability_requirements(route).process_unresolved)
    assert _assess(route).process.status is S.UNKNOWN


def test_f3_sequential_op_durations_add_and_contradict_a_smaller_record_ceiling():
    record = dc.replace(_CLEAN_RECORD, elapsed_minutes=Interval(0, 90, "min"))
    route = _route(_hold(60), _hold(60), _hold(60), process=record)
    assert any("contradictory time evidence" in u for u in compile_capability_requirements(route).process_unresolved)
    assert _assess(route, _bench(process_bounds=dc.replace(_FULL_BOUNDS, max_step_minutes=120.0))
                   ).process.status is S.UNKNOWN


def test_f3b_a_provable_ordered_floor_above_the_bench_limit_blocks():
    record = dc.replace(_CLEAN_RECORD, elapsed_minutes=None, min_elapsed_minutes=30.0)
    route = _route(_hold(60), _hold(60), _hold(60), process=record)
    reqs = compile_capability_requirements(route)
    assert reqs.process[0].min_elapsed_minutes == 180.0  # the timeline floor handed to the unchanged delegate
    bench = _bench(process_bounds=dc.replace(_FULL_BOUNDS, max_step_minutes=120.0, max_total_minutes=120.0))
    assert _assess(route, bench).process.status is S.BLOCKED


def test_d15_a_record_that_summarizes_its_ops_is_not_double_counted():
    record = dc.replace(_CLEAN_RECORD, elapsed_minutes=Interval(60, 60, "min"))
    route = _route(_hold(60), process=record)
    reqs = compile_capability_requirements(route)
    assert reqs.process_unresolved == () and reqs.process[0].min_elapsed_minutes is None
    bench = _bench(process_bounds=dc.replace(_FULL_BOUNDS, max_step_minutes=100.0, max_total_minutes=100.0))
    assert _assess(route, bench).process.status is S.FIT


def test_m86_law_an_envelope_duration_outside_the_record_is_not_fit():
    route = _route(duration=Interval(30240, 30240, "min"),
                   process=dc.replace(_CLEAN_RECORD, elapsed_minutes=Interval(0, 60, "min")))
    bench = _bench(process_bounds=dc.replace(_FULL_BOUNDS, max_step_minutes=50000.0, max_total_minutes=50000.0))
    assert _assess(route, bench).process.status in (S.UNKNOWN, S.BLOCKED)
    assert _assess(_route(), bench).process.status is S.FIT  # the control


_NO_LIMIT_TIME = frozenset({"max_step_minutes", "max_total_minutes", "max_active_minutes", "budget"})
_ONLY_NO_LIMIT = ProcessBounds.of(allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                                  allowed_agitation=tuple(Agitation))


@pytest.mark.parametrize("label, record, bounds, no_limit", [
    ("F-8a workup_included=False under NO_LIMIT",
     dc.replace(_CLEAN_RECORD, workup_included=False), _ONLY_NO_LIMIT, _NO_LIMIT_TIME),
    ("F-8b an EMPTY record under NO_LIMIT", ProcessRequirements(), _ONLY_NO_LIMIT, _NO_LIMIT_TIME),
    ("F-8c no record under NO_LIMIT", None, _ONLY_NO_LIMIT, _NO_LIMIT_TIME),
    ("F-8d no record, silent bench", None, ProcessBounds.unconstrained(), frozenset({"budget"})),
    ("F-8e empty record, silent bench", ProcessRequirements(), ProcessBounds.unconstrained(), frozenset({"budget"})),
    ("F-8f route silent on attention/agitation/active under NO_LIMIT",
     ProcessRequirements(workup_included=True, provenance="fixture", elapsed_minutes=Interval(0, 60, "min")),
     ProcessBounds.unconstrained(), _NO_LIMIT_TIME),
    ("F-8g PERIODIC with no check interval vs a preset-shaped bench",
     dc.replace(_CLEAN_RECORD, attention=Attention.PERIODIC),
     ProcessBounds.of(max_step_minutes=600.0, max_total_minutes=600.0, allowed_attention=tuple(Attention),
                      allowed_agitation=tuple(Agitation)), frozenset({"budget"})),
])
def test_f8_no_limit_and_silence_never_launder_a_missing_process_fact(label, record, bounds, no_limit):
    a = _assess(_route(process=record), _bench(process_bounds=bounds, no_limit_dimensions=no_limit))
    assert a.process.status is S.UNKNOWN, (label, a.process)


def test_f8_the_process_axis_is_never_unconstrained_for_a_real_step():
    a = _assess(_route(process=None), _bench(process_bounds=ProcessBounds.unconstrained()))
    assert a.process.status is not S.UNCONSTRAINED and a.process.status not in PASSES


def test_f8_no_limit_still_certifies_a_fully_declared_step_tagged_as_a_preference():
    a = _assess(_route(), _bench(process_bounds=_ONLY_NO_LIMIT, no_limit_dimensions=_NO_LIMIT_TIME))
    assert a.process.status is S.FIT
    assert any("NO_LIMIT preference, not measured capability" in r for r in a.process.reasons)


@pytest.mark.parametrize("field, text", [("rate", "dropwise over 3 hours via syringe pump"),
                                         ("agitation", "vigorous overhead mechanical stirring")])
def test_d16_a_present_rate_or_agitation_is_an_unread_process_demand(field, text):
    op = _op(OperationKind.ADD, **{field: _pf(text)})
    assert _assess(_route(op)).process.status is S.UNKNOWN


# ---------------------------------------------------------------------------------------------------------------
# D16 -- equipment / measurement per-op guards and the endpoint + amount laws (F-4, F-4b, P5b)
# ---------------------------------------------------------------------------------------------------------------

_T = _pf(Interval(298.15, 298.15, "K"))


@pytest.mark.parametrize("apparatus, expected", [
    (("simple distillation apparatus",), S.FIT),          # the control: a real (named) still
    (("distillation apparatus",), S.UNKNOWN),             # D24.16 / Wave-C' F1: configuration unnamed -> unread
    (("boiling stones",), S.UNKNOWN),                     # F-4: an ignored consumable is not a still
    (("glass rod", "dropper"), S.UNKNOWN),
    (("thermometer",), S.UNKNOWN),                        # F-4b: real hardware, wrong kind
    ((), S.UNKNOWN),
])
def test_f4_a_hardware_op_needs_an_admissible_non_consumable_capability(apparatus, expected):
    still = _op(OperationKind.DISTILL, apparatus=apparatus, temperature=_T)
    assert _assess(_route(still)).equipment.status is expected


def test_f4_the_step_record_equipment_never_discharges_an_op():
    record = dc.replace(_CLEAN_RECORD, equipment=("simple distillation apparatus",))
    still = _op(OperationKind.DISTILL, apparatus=("boiling stones",), temperature=_T)
    assert _assess(_route(still, process=record)).equipment.status is S.UNKNOWN


def test_p5b_a_second_verify_op_with_no_method_is_not_masked_by_the_first():
    weigh = _op(OperationKind.VERIFY, apparatus=("analytical balance",))
    spot = _op(OperationKind.VERIFY, materials=("ferric chloride",))
    assert _assess(_route(weigh)).measurement.status is S.FIT  # the control
    assert _assess(_route(weigh, spot)).measurement.status is S.UNKNOWN


def test_d16_a_present_endpoint_criterion_is_an_unread_measurement_demand():
    weigh = _op(OperationKind.VERIFY, apparatus=("analytical balance",))
    wash = _op(OperationKind.ADD, role=OperationRole.WASH, endpoint=_pf("wash until basic to litmus"))
    assert _assess(_route(weigh, wash)).measurement.status is S.UNKNOWN


def _with_op1_quantity(text):
    shown = _route(uses=_BASE_USES)
    op1 = dc.replace(shown.steps[0].envelope.procedure.operations[0], quantity=_pf(text))
    proc = dc.replace(shown.steps[0].envelope.procedure, operations=(op1,))
    return dc.replace(shown, steps=(dc.replace(shown.steps[0], envelope=dc.replace(
        shown.steps[0].envelope, procedure=proc)),))


def test_d16_an_amount_with_no_typed_home_is_material_unresolved_but_a_display_form_is_not():
    orphan = _op(OperationKind.FILTER, apparatus=("buchner funnel",), quantity=_pf("500 mL + 500 mL"))
    reqs = compile_capability_requirements(_route(orphan))
    assert any("not the canonical rendering" in u for u in reqs.material_unresolved)
    assert _assess(_route(orphan)).material.status is S.UNKNOWN
    # the control (D24.1): op1's quantity text IS the canonical rendering of its quantified typed uses -> display only
    route = _with_op1_quantity("10 mL methanol + 10 mL acetic acid")
    assert compile_capability_requirements(route).material_unresolved == ()
    assert _assess(route).material.status is S.FIT


@pytest.mark.parametrize("text", [
    "5 L methanol",                                    # A1a: a larger amount of a typed species
    "10 mL methanol + 10 mL acetic acid + 2 g sodium metal",  # A1b: a SECOND species the typed uses omit
    "10 mL methanol; sealed tube at 650 K and 50 atm for 3 days",  # A1c: conditions smuggled into the amount slot
    "10 mL methanol + 10 mL acid",                     # near-miss spelling: not byte-equal -> never display
])
def test_d24_1_a_quantity_prose_beside_typed_uses_is_display_only_when_canonical(text):
    """Wave-C' A1: the old "any quantified typed use makes op.quantity a display form" trust model let the prose state
    an amount, a second material or conditions no typed field carries. D24.1: display only when byte-equal to
    ``render_op_quantity(op)``; otherwise material_unresolved (host = MATERIAL) -> UNKNOWN."""
    route = _with_op1_quantity(text)
    assert any("not the canonical rendering" in u for u in compile_capability_requirements(route).material_unresolved)
    assert _assess(route).material.status is S.UNKNOWN


# ---------------------------------------------------------------------------------------------------------------
# D17 -- role consistency, medium, and order-aware external inputs (F-7, Part IV, S1, S2)
# ---------------------------------------------------------------------------------------------------------------

def test_f7_a_net_consumed_species_typed_catalyst_is_an_unresolved_role_claim():
    uses = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _ME),
            _use("acetic acid", ProcedureMaterialRole.CATALYST, _AC))
    reqs = compile_capability_requirements(_route(uses=uses))
    acid = [r for r in reqs.material if r.name == "acetic acid"]
    assert acid and any("role contradiction" in t for t in acid[0].specification.unresolved_terms)
    assert _assess(_route(uses=uses)).material.status is S.UNKNOWN


def test_f7_converse_a_stoichiometric_role_the_step_does_not_consume_is_unresolved():
    uses = _BASE_USES + (_use("water", ProcedureMaterialRole.REACTANT, _WATER),)
    reqs = compile_capability_requirements(_route(uses=uses))
    water = [r for r in reqs.material if r.name == "water"]
    assert water and any("does not net-consume" in t for t in water[0].specification.unresolved_terms)
    bench = _bench(_bottle("water-pure", _WATER))
    assert _assess(_route(uses=uses), bench).material.status is S.UNKNOWN


def test_part_iv_a_condition_sentence_in_the_medium_is_not_a_species():
    """Part IV stands: the sentence is never a species, a hazard entry or a waste stream. D24.3 (Wave-C' A5): it is
    still an open question about what material it might name, so it leaves a TEXT-FREE material_unresolved note
    (UNKNOWN) -- unless a typed use of that step exactly covers it."""
    sentence = "neat; acid-catalyzed (conc. H2SO4); reflux then fractional distillation"
    reqs = compile_capability_requirements(_route(medium=sentence))
    assert not any(r.name == sentence for r in reqs.material)
    assert not any(sentence in h for h in reqs.hazard_unresolved)
    assert not any(sentence in w for w in reqs.waste.unresolved + reqs.waste.reasons)
    notes = [u for u in reqs.material_unresolved if "envelope.medium" in u]
    assert notes and not any(sentence in u for u in notes)  # text-free: the sentence is not re-quoted as a thing
    assert _assess(_route(medium=sentence)).material.status is S.UNKNOWN
    assert _assess(_route()).material.status is S.FIT  # the control: no medium, no note


def test_d24_3_a_species_named_only_in_the_medium_of_a_procedure_step_is_never_fit():
    """Wave-C' A5: medium="benzene" on a step WITH ProcedureEvidence read no axis (material FIT on a bench with no
    benzene). D24.3: an uncovered medium is unread (UNKNOWN); a typed use of that step with the exact name covers it."""
    assert _assess(_route(medium="benzene")).material.status is S.UNKNOWN
    covered = _BASE_USES + (_use("benzene", ProcedureMaterialRole.SOLVENT, None),)
    reqs = compile_capability_requirements(_route(uses=covered, medium="benzene"))
    assert not any("envelope.medium" in u for u in reqs.material_unresolved)


def test_d17_a_step_with_no_procedure_evidence_is_material_unresolved():
    reqs = compile_capability_requirements(_route(procedure=False))
    assert any("no ProcedureEvidence" in u for u in reqs.material_unresolved)
    assert _assess(_route(procedure=False)).material.status is S.UNKNOWN


def _two_step(step1_uses):
    first = _route(uses=step1_uses).steps[0]
    second = ExperimentStep.assembling(_AC2O, (_MEOAC, _AC), (_AC2O, _ME), envelope=ConditionEnvelope.unknown())
    return ExperimentRoute(ROUTE_SCHEMA, (first, second))


def test_s1_a_later_steps_consumption_is_not_hidden_by_an_earlier_typed_use():
    route = _two_step(_BASE_USES)
    acid = [r for r in compile_capability_requirements(route).material
            if r.identity is not None and r.role == "reactant (leaf input)"]
    assert acid and "step 2" in acid[0].evidence_source, [r.label for r in acid]
    assert _assess(route).material.status is S.UNKNOWN


def test_s2_an_input_a_later_step_makes_is_still_an_external_input_of_the_earlier_step():
    route = _two_step((_use("acetic acid", ProcedureMaterialRole.REACTANT, _AC),))
    labels = [(r.role, r.evidence_source) for r in compile_capability_requirements(route).material]
    assert any(role == "reactant (leaf input)" and "step 1" in ev for role, ev in labels), labels


# ---------------------------------------------------------------------------------------------------------------
# D18 -- phase is an evidence-graded claim; CLAMPED never proves purity
# ---------------------------------------------------------------------------------------------------------------

def _phase_world(req_phase, req_ev, stock_phase, stock_ev):
    uses = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _ME),
            _use("acetic acid", ProcedureMaterialRole.REACTANT, _AC, phase=req_phase, ev=req_ev))
    bench = _bench(material_inventory=(_bottle("methanol-pure", _ME),
                                       _bottle("acetic", _AC, phase=stock_phase, phase_ev=stock_ev)))
    return _assess(_route(uses=uses), bench).material.status


def test_mp1_an_author_inferred_phase_matching_the_stock_does_not_certify_fit():
    assert _phase_world(Phase.LIQUID, _AI, Phase.LIQUID, _UD) is S.UNKNOWN


def test_mp2_an_author_inferred_phase_contradicting_the_stock_does_not_certify_blocked():
    assert _phase_world(Phase.LIQUID, _AI, Phase.SOLID, _UD) is S.UNKNOWN


def test_mp3_a_sourced_requirement_against_a_declared_stock_phase_decides_both_ways():
    assert _phase_world(Phase.LIQUID, _SQ, Phase.LIQUID, _UD) is S.FIT
    assert _phase_world(Phase.LIQUID, _SQ, Phase.SOLID, _UD) is S.BLOCKED


def test_mp4_a_stock_phase_with_no_evidence_cannot_certify():
    assert _phase_world(Phase.LIQUID, _SQ, Phase.LIQUID, _UNK) is S.UNKNOWN


def test_f5_a_clamped_unit_interval_is_not_a_purity_witness():
    clamp = _evidence("100", "101", kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, kind=_SQ,
                      unit=InputUnit.PERCENT)
    assert clamp.kind is EvidenceKind.CLAMPED and (clamp.low, clamp.high) == ("1", "1")
    bench = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("acetic-clamped", _AC, evidence=clamp)))
    assert _assess(_route(), bench).material.status is S.UNKNOWN


# ---------------------------------------------------------------------------------------------------------------
# D20 (assess side) -- an unknown readiness tier is malformed data (ValueError), never a KeyError
# ---------------------------------------------------------------------------------------------------------------

def test_d20_an_unknown_readiness_tier_is_refused_with_value_error():
    a = _assess(_route())
    clear = AxisResult(S.FIT, ("fixture",))
    with pytest.raises(ValueError, match="not a readiness tier"):
        CapabilityAssessment(
            schema_version=CAPABILITY_ASSESSMENT_SCHEMA, profile_digest=a.profile_digest, route_digest=a.route_digest,
            **{name: clear for name in ("material", "equipment", "physical", "process", "containment", "ventilation",
                                        "measurement", "waste", "procurement", "attention_care", "monetary")},
            overall=S.FIT, overall_reasons=("forged",), readiness_tier="BOGUS_TIER",
            readiness_digest=a.readiness_digest)


# ---------------------------------------------------------------------------------------------------------------
# D24 -- the post-Wave-C' amendment (audit §7.5): each regression below reproduces a Wave C' adversary's break on a
# micro world whose OTHER axes are clean, and pins the law that closes it. Every one was a per-axis false FIT (or a
# false BLOCK) on the D14-D22 tree (941946a).
# ---------------------------------------------------------------------------------------------------------------

from smartchem.capability.coverage import render_op_quantity, render_scale, render_summary, render_verification  # noqa: E402
from smartchem.capability.requirements import WasteRequirement  # noqa: E402
from smartchem.data import material_library as lib  # noqa: E402
from smartchem.decompiler_conditions import _SPEC_SATURATED_AQUEOUS_NACL  # noqa: E402
from smartchem.experiment.stock import MATERIAL_COMPONENT_SCHEMA  # noqa: E402
from smartchem.material_spec import (  # noqa: E402
    DilutionState,
    HydrationState,
    MaterialSpecification,
    SaturationState,
    StateClaim,
)
from smartchem.provenance import SourceCitation, SourceReview  # noqa: E402

_STILL = _op(OperationKind.DISTILL, apparatus=("simple distillation apparatus",), temperature=_T)
_DRY = _op(OperationKind.DRY, apparatus=("erlenmeyer flask",))
_QUENCH = _op(OperationKind.ADD, role=OperationRole.QUENCH)
_VERIFY_MASS = _op(OperationKind.VERIFY, apparatus=("analytical balance",))


def _replace_procedure(route, **changes):
    step = route.steps[0]
    proc = dc.replace(step.envelope.procedure, **changes)
    return dc.replace(route, steps=(dc.replace(step, envelope=dc.replace(step.envelope, procedure=proc)),))


def _canonical(proc, field):
    if field == "scale":
        return render_scale(proc)
    if field == "analytical_verification":
        return render_verification(proc)
    return render_summary(proc, field)


@pytest.mark.parametrize("field, host, prose, axis", [
    # Wave-C' A3: a PRESENT summary is what EARNS PROCESS_SPECIFIED -- the HARD LAW is not its backstop.
    ("purification", _STILL, "vacuum distillation at 1 mmHg, bp 80 C", "process"),
    ("drying", _DRY, "vacuum oven 0.01 atm 390 K 48 h", "process"),
    ("quench", _QUENCH, "dry-ice/acetone 195 K", "process"),
    ("scale", None, "5 L methanol in a 20 L reactor", "material"),
    # Wave-C' A2: the verification text named methods no VERIFY op types.
    ("analytical_verification", _VERIFY_MASS, "1H NMR and HPLC purity >= 99.5 %", "measurement"),
])
def test_d24_1_a_procedure_summary_is_display_only_when_it_is_the_canonical_rendering(field, host, prose, axis):
    base = _route(*(() if host is None else (host,)))
    canonical = _canonical(base.steps[0].envelope.procedure, field)
    assert canonical, "the typed fields must render to something for the control to be meaningful"
    control = _replace_procedure(base, **{field: _pf(canonical)})
    witness = _replace_procedure(base, **{field: _pf(prose)})
    assert getattr(_assess(control), axis).status in PASSES, getattr(_assess(control), axis).reasons
    assert getattr(_assess(witness), axis).status is S.UNKNOWN


def test_d24_1_a_vacuum_op_needs_a_sub_atmospheric_whole_step_minimum():
    """Wave-C' A3 (pressure side): a Buchner (vacuum) filtration states a sub-atmospheric demand of unstated size."""
    vac = _op(OperationKind.FILTER, apparatus=("buchner funnel",))
    bench = _bench(physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, min_temperature_k=250.0,
                                                     min_pressure_atm=0.1, max_pressure_atm=2.0))
    assert _assess(_route(vac), bench).physical.status is S.UNKNOWN  # the clean record claims 1 atm: contradiction
    unread = dc.replace(_CLEAN_RECORD, min_pressure_atm=None)
    assert _assess(_route(vac, process=unread), bench).physical.status is S.UNKNOWN
    covered = dc.replace(_CLEAN_RECORD, min_pressure_atm=0.2)
    assert _assess(_route(vac, process=covered), bench).physical.status is S.FIT


def test_d24_4_a_mix_op_is_an_agitation_demand_the_record_must_carry():
    """Wave-C' A6: a MIX op reached no axis (record agitation NONE, bench allowing NONE -> process FIT)."""
    mix = _op(OperationKind.MIX)
    assert _assess(_route(mix)).process.status is S.UNKNOWN
    assert _assess(_route(mix, process=dc.replace(_CLEAN_RECORD, agitation=None))).process.status is S.UNKNOWN
    assert _assess(_route(mix, process=dc.replace(_CLEAN_RECORD, agitation=Agitation.MANUAL))).process.status is S.FIT


def test_d24_1_formulation_words_beside_an_empty_specification_are_unresolved():
    """Wave-C' A9: an EMPTY spec typed nothing, so "anhydrous (<= 50 ppm H2O)" was silently dropped (material FIT)."""
    worded = dc.replace(_BASE_USES[1], formulation="anhydrous (<= 50 ppm H2O)", specification=MaterialSpecification())
    assert _assess(_route(uses=(_BASE_USES[0], worded))).material.status is S.UNKNOWN
    plain = dc.replace(worded, formulation=None)
    assert _assess(_route(uses=(_BASE_USES[0], plain))).material.status is S.FIT


def test_d24_3_b3_a_solvent_named_only_in_condition_prose_is_never_fit():
    """Wave-C' B3a: medium="reflux in 50 mL toluene" on a procedure step read no axis."""
    assert _assess(_route(medium="reflux in 50 mL toluene")).material.status is S.UNKNOWN


# -- D24.5: commensurability is EARNED (Wave-C' B1 A-G, C1) ---------------------------------------------------------

def _state(state, ev=_UD):
    return StateClaim(state, ev)


def _solid_bottle(mid, *components, qty="10", unit="g", phase=Phase.SOLID):
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, tuple(components), phase, "fixture: operator-declared bottle",
                         quantity=StockQuantity.of(qty, unit), phase_evidence=_UD)


def _drier_world(bottle, *, spec, qty="10", name="drier s", phase=Phase.SOLID):
    drier = ProcedureMaterialUse(name=name, role=ProcedureMaterialRole.DRY, phase=PhaseClaim(phase, _SQ),
                                 quantity=StockQuantity.of(qty, "g" if phase is Phase.SOLID else "mL"),
                                 evidence_source="fixture micro-route", specification=spec)
    bench = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("acetic-pure", _AC), bottle))
    return _assess(_route(uses=_BASE_USES + (drier,)), bench).material.status


_ANHYDROUS_SQ = MaterialSpecification(states=(_state(HydrationState.ANHYDROUS, _SQ),))


def test_d24_5_b1_a_state_word_never_turns_a_one_percent_bottle_into_a_proven_draw():
    dilute = _solid_bottle("drier-1pct",
                           MaterialComponent.evidenced("drier s", "active", _evidence("0.01", "0.01"),
                                                       states=(_state(HydrationState.ANHYDROUS),)),
                           MaterialComponent.evidenced("sand", "filler", _evidence("0.99", "0.99")))
    assert _drier_world(dilute, spec=_ANHYDROUS_SQ) is S.UNKNOWN                    # B1-A (was FIT)
    assert _drier_world(dilute, spec=MaterialSpecification()) is S.UNKNOWN          # B1-B monotone control
    pure = _solid_bottle("drier-pure", MaterialComponent.evidenced("drier s", "active", _evidence(),
                                                                   states=(_state(HydrationState.ANHYDROUS),)))
    assert _drier_world(pure, spec=_ANHYDROUS_SQ) is S.FIT                          # B1-C clean control


def test_d24_5_b1_d_an_undiluted_claim_on_a_one_percent_component_is_not_a_proven_draw():
    neat_req = MaterialSpecification(states=(_state(DilutionState.NEAT, _SQ),))
    acid = dc.replace(_BASE_USES[1], specification=neat_req)
    one_pct = StockMaterial(STOCK_MATERIAL_SCHEMA, "acid-1pct", "acid-1pct", (
        MaterialComponent.evidenced(_AC, "active", _evidence("0.01", "0.01"), states=(_state(DilutionState.NEAT),)),
        MaterialComponent.evidenced(_WATER, "solvent", _evidence("0.99", "0.99"))),
        Phase.LIQUID, "fixture", quantity=StockQuantity.of("500", "mL"), phase_evidence=_UD)
    bench = _bench(material_inventory=(_bottle("methanol-pure", _ME), one_pct))
    assert _assess(_route(uses=(_BASE_USES[0], acid)), bench).material.status is not S.FIT


def test_d24_5_b1_e_a_component_listed_at_zero_is_absent():
    phantom = _solid_bottle("sand", MaterialComponent.evidenced("sand", "filler", _evidence()),
                            MaterialComponent.evidenced("drier s", "active", _evidence("0", "0"),
                                                        states=(_state(HydrationState.ANHYDROUS),)))
    assert _drier_world(phantom, spec=_ANHYDROUS_SQ) is S.BLOCKED  # provably absent, never a proven draw


def test_d24_5_b1_f_the_clamped_library_drier_is_no_longer_a_proven_draw_through_a_state_word():
    """The real library bottle (assay CLAMPED [0.97, 1], ANHYDROUS declared): D18 already refuses CLAMPED as a purity
    witness; the state-only spec was a back door around it (B1-F)."""
    drier = lib.magnesium_sulfate_anhydrous(quantity=StockQuantity.of("2", "g"))
    assert _drier_world(drier, spec=_ANHYDROUS_SQ, qty="2", name="magnesium sulfate") is S.UNKNOWN


def test_d24_5_b1_g_the_live_corpus_brine_spec_needs_a_certified_positive_fraction():
    """The LIVE corpus spec (SATURATED + SOLUTION, source-quoted aqueous phase): plain water that LISTS the solute at
    [0, 0] with a saturation claim is not brine (B1-G); the real library brine (DERIVED fraction > 0) is."""
    phantom = StockMaterial(STOCK_MATERIAL_SCHEMA, "plain-water", "plain water", (
        MaterialComponent.evidenced(_WATER, "solvent", _evidence()),
        MaterialComponent.evidenced("sodium chloride", "active", _evidence("0", "0"), states=(
            _state(SaturationState.SATURATED), _state(DilutionState.SOLUTION)))),
        Phase.AQUEOUS_SOLUTION, "fixture", quantity=StockQuantity.of("5", "mL"), phase_evidence=_UD)
    kw = dict(spec=_SPEC_SATURATED_AQUEOUS_NACL, qty="5", name="sodium chloride", phase=Phase.AQUEOUS_SOLUTION)
    assert _drier_world(phantom, **kw) is not S.FIT
    brine = lib.sodium_chloride_saturated_wash(quantity=StockQuantity.of("5", "mL"))
    assert _drier_world(brine, **kw) is S.FIT  # liveness: a real formulated draw is still commensurable


@pytest.mark.parametrize("basis, value", [(ConcentrationBasis.MASS_PER_VOLUME, 0.3), (ConcentrationBasis.MOLAR, 6.0)])
def test_d24_5_c1_the_pure_witness_reads_the_whole_bottle(basis, value):
    """Wave-C' C1: "methanol [1, 1]" beside 0.3 g/mL (or 6 M) of a second species is a contradictory bottle. Two layers
    now pin it: D25.2 (Wave-C'' NEW-2) REFUSES the bottle at construction -- a species at mass-fraction lower bound 1
    leaves no room for any other positive amount on ANY basis -- and, as defence in depth for a bottle smuggled past
    construction, the D24.5 whole-bottle witness still reads every other component."""
    parts = (MaterialComponent.evidenced(_ME, "active", _evidence()),
             MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "sodium chloride", "solute", value, value, basis))
    with pytest.raises(ValueError, match="D25.2"):
        StockMaterial(STOCK_MATERIAL_SCHEMA, "methanol-plus", "methanol-plus", parts, Phase.LIQUID, "fixture",
                      quantity=StockQuantity.of("500", "mL"), phase_evidence=_UD)
    smuggled = StockMaterial(STOCK_MATERIAL_SCHEMA, "methanol-plus", "methanol-plus", parts[:1], Phase.LIQUID,
                             "fixture", quantity=StockQuantity.of("500", "mL"), phase_evidence=_UD)
    object.__setattr__(smuggled, "components", parts)  # a keyless in-memory bypass of __post_init__
    bench = _bench(material_inventory=(smuggled, _bottle("acetic-pure", _AC)))
    assert _assess(_route(), bench).material.status is S.UNKNOWN
    assert _assess(_route()).material.status is S.FIT  # the clean control: a truly pure bottle


def test_d24_6_b2_one_condensation_byproduct_is_never_consumed_for_free_by_a_later_step():
    """Wave-C' B2: step 1's water byproduct (removed in its workup) fed a later hydrolysis with no demand at all."""
    first = _route().steps[0]
    hydrolysis = ExperimentStep(STEP_SCHEMA, _AC, (_MEOAC, _WATER), (_AC, _ME), (), _envelope(uses=()))
    route = ExperimentRoute(ROUTE_SCHEMA, (first, hydrolysis))
    water = [r for r in compile_capability_requirements(route).material
             if r.identity is not None and r.role == "reactant (leaf input)" and "step 2" in r.evidence_source]
    assert water, "the later consumption of a byproduct is an external demand of its own (D24.6)"
    assert _assess(route).material.status is not S.FIT


def test_d24_8_c6_a_name_keyed_listing_is_not_proof_of_absence():
    by_name = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("acid-by-name", "acetic acid")))
    assert _assess(_route(), by_name).material.status is S.UNKNOWN          # was BLOCKED (C6 false BLOCK)
    other = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("benzene-by-name", "benzene")))
    assert _assess(_route(), other).material.status is S.BLOCKED            # a different name is still absence


def test_d24_17_a_step_with_no_procedure_evidence_has_unread_equipment_and_verification_demands():
    a = _assess(_route(procedure=False))
    assert a.equipment.status is S.UNKNOWN and a.measurement.status is S.UNKNOWN
    control = _assess(_route())
    assert control.equipment.status is S.NOT_APPLICABLE and control.measurement.status is S.NOT_APPLICABLE


# -- reachability: the D24 laws leave CAPABILITY_FIT reachable in a FULLY TYPED world -----------------------------

def test_d24_a_fully_typed_world_still_reaches_every_axis_fit_except_waste():
    """The model-consistency proof (Part VII): a real PROCESS_SPECIFIED route (2 MeOH -> DME + H2O, the real
    capped-scission step) whose sourced procedure types EVERYTHING -- canonical scale / summaries / verification,
    typed conditions, a gravity (not vacuum) filtration -- passes every axis but waste, and reaches overall FIT once
    only the waste requirement is discharged. None of D14-D24 is overconstrained; the ceiling is the missing
    disposition vocabulary (0.9.5 StreamDisposition)."""
    from tests.test_poor_man_reaction_type_oracle import _routes

    dme = next(r.steps[0] for r in _routes("COC", ["methanol"]) if len(r.steps) == 1)
    meoh = dme.reactants[0]
    src = SourceCitation("https://example.test/procedure", SourceReview.ACCEPTED)
    add = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, locator="src p.1",
                             material_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, meoh, qty="20"),),
                             duration=_pf(Interval(30, 30, "min"), "src p.1"))
    filt = ProcedureOperation(ordinal=2, kind=OperationKind.FILTER, locator="src p.1", apparatus=("fluted filter paper",))
    weigh = ProcedureOperation(ordinal=3, kind=OperationKind.VERIFY, locator="src p.1", apparatus=("analytical balance",))
    na = EvidenceField.not_applicable("src p.1", "the source closes this out")
    draft = ProcedureEvidence(reaction_scope="2 MeOH -> DME", source=src, scale=_pf("x", "src p.1"),
                              operations=(add, filt, weigh), quench=na, workup_isolation=_pf("x", "src p.1"),
                              separation=na, wash=na, drying=na, purification=na,
                              analytical_verification=_pf("x", "src p.1"))
    proc = dc.replace(draft, scale=_pf(render_scale(draft), "src p.1"),
                      workup_isolation=_pf(render_summary(draft, "workup_isolation"), "src p.1"),
                      analytical_verification=_pf(render_verification(draft), "src p.1"))
    envelope = ConditionEnvelope(procedure=proc, process=_CLEAN_RECORD, temperature=Interval(298.15, 298.15, "K"),
                                 pressure=Interval(1.0, 1.0, "atm"), status=EvidenceStatus.EXPERIMENTAL,
                                 provenance="declared conditions", source=src)
    route = ExperimentRoute(ROUTE_SCHEMA, (dc.replace(dme, envelope=envelope),))
    readiness = evaluate_route(route)
    assert readiness.tier == "PROCESS_SPECIFIED", readiness.tier
    bench = _bench(material_inventory=(_bottle("methanol-pure", meoh),))
    reqs = compile_capability_requirements(route)
    honest = assess(bench, reqs, readiness)
    blockers = {name for name in ("material", "equipment", "physical", "process", "containment", "ventilation",
                                  "measurement", "waste", "procurement", "attention_care", "monetary")
                if getattr(honest, name).status not in PASSES}
    assert blockers == {"waste"}, {n: getattr(honest, n).reasons for n in blockers}
    discharged = assess(bench, dc.replace(reqs, waste=WasteRequirement(frozenset(), ())), readiness)
    assert discharged.overall is S.FIT


# -- D25 (Wave-C'' fresh non-author confirmation pass) ------------------------------------------------------------

def test_d25_1_new1_a_demand_smuggled_into_an_identity_bearing_use_name_is_unread():
    """Wave-C'' NEW-1: the canonical renderers build from use NAMES, and an identity-bearing use's name was read by
    nothing -- so "methanol + 2 g sodium metal in a sealed tube at 650 K" beside a canonical op.quantity certified FIT.
    D25.1: a name that is not a resolvable NAME of its own identity is an unread material demand."""
    carrier = "methanol + 2 g sodium metal in a sealed tube at 650 K"
    uses = (_use(carrier, ProcedureMaterialRole.SUBSTRATE, _ME), _BASE_USES[1])
    route = _route(uses=uses)
    op1 = route.steps[0].envelope.procedure.operations[0]
    shown = _replace_op1_quantity(route, render_op_quantity(op1))  # the byte-equal canonical rendering
    reqs = compile_capability_requirements(shown)
    assert any("D25.1" in u and carrier in u for u in reqs.material_unresolved)
    assert _assess(shown).material.status is S.UNKNOWN
    # control: the resolvable name, same canonical-rendering construction -> no D25.1 note, material FIT
    clean = _replace_op1_quantity(_route(), render_op_quantity(_route().steps[0].envelope.procedure.operations[0]))
    assert not any("D25.1" in u for u in compile_capability_requirements(clean).material_unresolved)
    assert _assess(clean).material.status is S.FIT


def test_d25_1_a_name_the_offline_resolver_does_not_know_is_an_unread_demand_not_a_crash():
    """A plain but unregistered name ("cold water" style modifiers, or a name absent from the offline table) is not
    verifiable, so it fails closed as an unread demand -- never a crash, never FIT."""
    uses = (_use("chilled methanol", ProcedureMaterialRole.SUBSTRATE, _ME), _BASE_USES[1])
    reqs = compile_capability_requirements(_route(uses=uses))
    assert any("D25.1" in u and "chilled methanol" in u for u in reqs.material_unresolved)


def test_d25_4_c6_on_the_real_leaf_path_a_resolvable_name_key_is_a_possible_source():
    """Wave-C'' C6: the projection's leaf-input requirements carry NO name, so D24.8 never fired on the real path.
    D25.4: a name-keyed bottle whose name RESOLVES to the leaf's own structure is a possible source (UNKNOWN), and a
    name the resolver maps elsewhere (or not at all) stays not-this-species (BLOCKED)."""
    only_methanol = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _ME),)  # acetic acid is an UNTYPED leaf
    route = _route(uses=only_methanol)
    leaf = [r for r in compile_capability_requirements(route).material if r.role == "reactant (leaf input)"]
    assert leaf and all(r.name is None for r in leaf)
    by_name = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("acid-by-name", "acetic acid")))
    assert _assess(route, by_name).material.status is S.UNKNOWN            # was BLOCKED before D25.4
    other = _bench(material_inventory=(_bottle("methanol-pure", _ME), _bottle("benzene-by-name", "benzene")))
    assert _assess(route, other).material.status is S.BLOCKED


def _replace_op1_quantity(route, text):
    step = route.steps[0]
    op1 = dc.replace(step.envelope.procedure.operations[0], quantity=_pf(text))
    ops = (op1,) + step.envelope.procedure.operations[1:]
    proc = dc.replace(step.envelope.procedure, operations=ops)
    return dc.replace(route, steps=(dc.replace(step, envelope=dc.replace(step.envelope, procedure=proc)),))
