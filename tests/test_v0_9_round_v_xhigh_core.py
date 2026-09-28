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
    still = _op(OperationKind.DISTILL, apparatus=("distillation apparatus",))
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
    (("distillation apparatus",), S.FIT),                 # the control: a real still
    (("boiling stones",), S.UNKNOWN),                     # F-4: an ignored consumable is not a still
    (("glass rod", "dropper"), S.UNKNOWN),
    (("thermometer",), S.UNKNOWN),                        # F-4b: real hardware, wrong kind
    ((), S.UNKNOWN),
])
def test_f4_a_hardware_op_needs_an_admissible_non_consumable_capability(apparatus, expected):
    still = _op(OperationKind.DISTILL, apparatus=apparatus, temperature=_T)
    assert _assess(_route(still)).equipment.status is expected


def test_f4_the_step_record_equipment_never_discharges_an_op():
    record = dc.replace(_CLEAN_RECORD, equipment=("distillation apparatus",))
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


def test_d16_an_amount_with_no_typed_home_is_material_unresolved_but_a_display_form_is_not():
    orphan = _op(OperationKind.FILTER, apparatus=("buchner funnel",), quantity=_pf("500 mL + 500 mL"))
    reqs = compile_capability_requirements(_route(orphan))
    assert any("F69-analog" in u for u in reqs.material_unresolved)
    assert _assess(_route(orphan)).material.status is S.UNKNOWN
    # the control: op1's typed quantified uses make its own quantity text a display form
    shown = _route(uses=_BASE_USES)
    op1 = dc.replace(shown.steps[0].envelope.procedure.operations[0], quantity=_pf("10 mL methanol + 10 mL acid"))
    proc = dc.replace(shown.steps[0].envelope.procedure, operations=(op1,))
    route = dc.replace(shown, steps=(dc.replace(shown.steps[0], envelope=dc.replace(
        shown.steps[0].envelope, procedure=proc)),))
    assert compile_capability_requirements(route).material_unresolved == ()
    assert _assess(route).material.status is S.FIT


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
    sentence = "neat; acid-catalyzed (conc. H2SO4); reflux then fractional distillation"
    reqs = compile_capability_requirements(_route(medium=sentence))
    assert not any(r.name == sentence for r in reqs.material)
    assert not any(sentence in h for h in reqs.hazard_unresolved)
    assert _assess(_route(medium=sentence)).material.status is S.FIT


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
