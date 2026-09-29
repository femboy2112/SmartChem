"""v0.9 RC Round V -- capability-core knife-edges (barrier D1, D2, D3 consumption, D10 wiring, D13 amendment).

*Burp.* Every test here runs on the REAL objects -- ``QuantityDemand``, ``MaterialRequirement``, ``StockMaterial``,
``assess()`` and ``compile_capability_requirements()`` on the searched, sourced isopentyl route -- never on the Lane A
scratch prototype. What they pin:

* D1  -- quantity knowledge: exact decimal sums, unstated uses COUNTED, mixed units kept apart, never ``None``;
* D2  -- ONE global exact allocation per unit domain; no bottle spent twice (species, spec split, name/structure key,
         unit domain); no epsilon (0.1+0.2 == 0.3 exactly; 20.00004 > 20);
* D3-D6 consumption -- the material axis reads ``compare_specification`` (F69 unresolved term, M70 unknown basis,
         M71 ASSUMED-only agreement are all UNKNOWN, never FIT);
* D10 -- the process axis reads the declaration state (UNDECLARED / DECLARED_BOUND / NO_LIMIT);
* D13 -- a demand stated anywhere reaches its axis or that axis fails closed (Lane G K1b/K2/X1/X2/F1/F2 fixtures);
* the grep law -- the compiler/assessor source carries no formulation vocabulary and no reagent identities.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
from fractions import Fraction

import pytest

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import CAPABILITY_ASSESSMENT_SCHEMA, _material_axis, assess
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    VentilationCapability,
    WasteCapability,
)
from smartchem.capability.presets import _bench_process_bounds, custom, isopentyl_capability_fit_bench
from smartchem.capability.profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile
from smartchem.capability.quantity import QuantityDemand, QuantityKnowledge, fraction_to_decimal
from smartchem.capability.requirements import (
    MaterialRequirement,
    RouteCapabilityRequirements,
    WasteRequirement,
    compile_capability_requirements,
)
from smartchem.conditions import Interval
from smartchem.constraints import PhysicalBounds
from smartchem.data import material_library
from smartchem.data.material_library import household_white_vinegar
from smartchem.data.reagents import Availability, commodity_for
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import CareLevel
from smartchem.experiment.readiness import ObligationStatus, RouteReadiness, StepReadiness, evaluate_route
from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute
from smartchem.experiment.stock import (
    MATERIAL_COMPONENT_SCHEMA,
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
    stock_material_from_commodity,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    MaterialSpecification,
    PhaseClaim,
    StateClaim,
    Tolerance,
)
from smartchem.procedure_evidence import EvidenceField, OperationKind, ProcedureMaterialRole
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)
_Q = StockQuantity.of

# =============================================================================================================
# plumbing
# =============================================================================================================


def _mol(name):
    return resolve_target(name, InputKind.AUTO).canonical()


@pytest.fixture(scope="module")
def iso_route():
    target = resolve_target("isopentyl acetate", InputKind.NAME).canonical()
    reagents = tuple(_mol(s) for s in ("water", "acetic acid"))
    have = (_mol("isopentyl alcohol"),)
    result = rt.search_routes(target, reagents=reagents, available=have, max_depth=3, registry=_CERTIFIED)
    for route in result.routes:
        if any(step.envelope.procedure is not None for step in route.steps):
            return route
    raise AssertionError("expected the sourced isopentyl route")


def _bottle(mid, comps, qty=None, phase=Phase.LIQUID, states=(), phase_ev=None):
    # Wave-C K1: state claims are COMPONENT-scoped; a fixture's claims are declared on every component it names.
    # X-high D18: a known fixture phase is the bench operator's own declaration (USER_DECLARED) unless told otherwise.
    comps = tuple(dataclasses.replace(c, states=tuple(states)) if states else c for c in comps)
    if phase_ev is None:
        phase_ev = EvidenceKind.UNKNOWN if phase is Phase.UNKNOWN else EvidenceKind.USER_DECLARED
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, comps, phase, "round-v core fixture", quantity=qty,
                         phase_evidence=phase_ev)


def _user_declared_pure():
    """A USER_DECLARED [1, 1] MASS_FRACTION record -- Wave-C K2: "provably pure" needs a fraction basis AND
    certifying evidence; a bare ``1.0`` (UNKNOWN strength, UNKNOWN basis) is never a proven draw."""
    from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
    return IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="round-v core fixture: the operator's own declaration about their bottle")


def _pure(name, qty, mid=None):
    return _bottle(mid or f"{name}-pure", (MaterialComponent.evidenced(name, "active", _user_declared_pure()),), qty)


def _ud(name, lo, hi, role="active"):
    """An operator-declared (USER_DECLARED) MASS_FRACTION component -- D24.5: a formulation-defining state makes a draw
    commensurable only over a CERTIFIED positive fraction, so allocation fixtures declare their fractions."""
    from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
    record = IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="round-v core fixture: the operator's own declaration about their bottle")
    return MaterialComponent.evidenced(name, role, record)


def _req(name, known=(), unstated=0, spec=None, phase=None, identity=None):
    # X-high D18: a fixture requirement phase is a SOURCE_QUOTED claim (the certifying case); pass a PhaseClaim to vary.
    if phase is not None and not isinstance(phase, PhaseClaim):
        phase = PhaseClaim(phase, EvidenceKind.SOURCE_QUOTED)
    return MaterialRequirement(
        identity=identity, phase=phase, quantity=QuantityDemand(tuple(known), unstated), role="fixture",
        evidence_source="round-v core fixture", name=name,
        specification=spec if spec is not None else MaterialSpecification(),
    )


def _status(reqs, inventory):
    return _material_axis(tuple(reqs), tuple(inventory)).status


_SOLUTION_REQ = MaterialSpecification(states=(StateClaim(DilutionState.SOLUTION, EvidenceKind.SOURCE_QUOTED),))
_SOLUTION_STOCK = (StateClaim(DilutionState.SOLUTION, EvidenceKind.USER_DECLARED),)


def _ps_readiness() -> RouteReadiness:
    step = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="fixture", conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.SATISFIED, workup_isolation=ObligationStatus.SATISFIED,
        provenance=("https://example.test/x",), open_obligations=(),
    )
    return RouteReadiness(per_step=(step,), route_open_obligations=())


def _reqs(**over) -> RouteCapabilityRequirements:
    base = dict(
        route_digest="rd", material=(), equipment=frozenset(), equipment_unrecognized=(),
        physical=PhysicalBounds.unconstrained(), process=(None,), containment=frozenset(),
        containment_reasons=(), hazard_unresolved=(), measurement=frozenset(),
        measurement_unrecognized=(), waste=WasteRequirement(frozenset(), ()),
        procurement_catalysts=(), attention_care=CareLevel.UNKNOWN, monetary=CostVector(),
    )
    base.update(over)
    return RouteCapabilityRequirements(**base)


def _profile(**over) -> CapabilityProfile:
    base = dict(
        schema_version=CAPABILITY_PROFILE_SCHEMA, profile_id="fixture", material_inventory=(),
        equipment=frozenset(), physical_bounds=PhysicalBounds.unconstrained(),
        process_bounds=ProcessBounds.unconstrained(), containment=frozenset(), ventilation=frozenset(),
        measurement=frozenset(), waste_handling=frozenset(), procurement=frozenset(), budget=None,
        provenance="fixture",
    )
    base.update(over)
    return CapabilityProfile(**base)


def _rebuild(route, env_fn):
    steps = list(route.steps)
    steps[0] = dataclasses.replace(steps[0], envelope=env_fn(steps[0].envelope))
    return ExperimentRoute(ROUTE_SCHEMA, tuple(steps))


def _map_ops(env, op_fn):
    proc = env.procedure
    return dataclasses.replace(env, procedure=dataclasses.replace(
        proc, operations=tuple(op_fn(op) for op in proc.operations)))


def _open_bench(inventory, **kw):
    args = dict(profile_id="round-v-open", material_inventory=tuple(inventory),
                equipment=frozenset(EquipmentCapability), containment=frozenset({ContainmentCapability.FUME_HOOD}),
                ventilation=frozenset({VentilationCapability.INDOOR}), measurement=frozenset(MeasurementMethod),
                waste_handling=frozenset(WasteCapability),
                procurement=frozenset(Availability) - frozenset({Availability.INDUSTRIAL}))
    args.update(kw)
    return custom(**args)


def _pick(tag):
    return next(s for s in material_library.isopentyl_fully_declared_inventory() if tag in s.material_id)


# =============================================================================================================
# D1 -- the quantity-knowledge algebra
# =============================================================================================================

def test_quantity_combine_is_exact_counts_unstated_and_keeps_units_apart():
    d = QuantityDemand.combine([_Q("0.1", "mL"), _Q("0.2", "mL"), None, _Q("10", "g"), None])
    assert d.known == (("g", "10"), ("mL", "0.3"))
    assert d.unstated_uses == 2
    assert d.knowledge is QuantityKnowledge.LOWER_BOUND_PLUS_UNKNOWN
    assert d.exact_by_unit() == {"g": Fraction(10), "mL": Fraction(3, 10)}
    assert QuantityDemand.combine([_Q("25", "mL")]).knowledge is QuantityKnowledge.EXACT
    assert QuantityDemand.combine([None]).knowledge is QuantityKnowledge.UNKNOWN
    # units compared by EXACT stripped string -- no conversion engine: L and mL are different domains.
    assert QuantityDemand.combine([_Q("1", "L"), _Q("1", "mL")]).known == (("L", "1"), ("mL", "1"))
    # canonical decimal form: equal demands digest equal.
    assert QuantityDemand((("mL", "20.0"),), 0) == QuantityDemand((("mL", "20"),), 0)
    assert fraction_to_decimal(Fraction(2000004, 100000)) == "20.00004"


def test_quantity_demand_is_never_none_and_refuses_the_empty_and_the_inexact():
    with pytest.raises(ValueError):
        QuantityDemand((), 0)
    with pytest.raises(ValueError):
        QuantityDemand((("mL", "1/3"),), 0)
    with pytest.raises(ValueError):
        QuantityDemand((("mL", "0"),), 0)
    with pytest.raises(TypeError):
        MaterialRequirement(identity=None, phase=None, quantity=None, role="r", evidence_source="e", name="A")


# =============================================================================================================
# D2 -- the global allocation knife-edges (Lane A, on real objects)
# =============================================================================================================

def test_f64_known_plus_unstated_is_never_fit_and_a_short_known_floor_blocks():
    demand = [("mL", "35")]
    assert _status([_req("A", demand, unstated=1)], [_pure("A", _Q("1000", "mL"))]) is CapabilityStatus.UNKNOWN
    assert _status([_req("A", demand, unstated=1)], [_pure("A", _Q("20", "mL"))]) is CapabilityStatus.BLOCKED
    # control: the same known demand, fully stated, FITs the big bottle.
    assert _status([_req("A", demand)], [_pure("A", _Q("1000", "mL"))]) is CapabilityStatus.FIT


def test_f65_mixed_units_never_collapse_to_no_gate():
    demand = [("g", "10"), ("mL", "20")]
    assert _status([_req("A", demand)], [_pure("A", _Q("0.001", "mL"))]) is CapabilityStatus.BLOCKED
    # ample mL, no g-denominated stock (no density bridge) -> UNKNOWN, never FIT
    assert _status([_req("A", demand)], [_pure("A", _Q("1000", "mL"))]) is CapabilityStatus.UNKNOWN


def test_f66_one_package_is_spent_once_across_species():
    ab = [_ud("A", "0.5", "0.5"), _ud("B", "0.5", "0.5")]
    reqs = [_req("A", [("mL", "80")], spec=_SOLUTION_REQ), _req("B", [("mL", "80")], spec=_SOLUTION_REQ)]
    one = [_bottle("ab", ab, _Q("100", "mL"), states=_SOLUTION_STOCK)]
    two = one + [_bottle("ab2", ab, _Q("100", "mL"), states=_SOLUTION_STOCK)]
    assert _status(reqs, one) is CapabilityStatus.BLOCKED
    assert _status(reqs, two) is CapabilityStatus.FIT


def test_f75_structure_key_and_name_key_of_one_bottle_are_one_package():
    acid = _mol("acetic acid")
    bottle = _bottle("twokey", (MaterialComponent.of_molecule(acid, "active", 1.0, 1.0),
                                MaterialComponent.unknown_fraction("acetic acid", "label")), _Q("100", "mL"))
    by_structure = _req("acetic acid", [("mL", "80")], identity=acid)
    by_name = _req("acetic acid", [("mL", "80")])
    status = _status([by_structure, by_name], [bottle])
    assert status is not CapabilityStatus.FIT
    assert status is CapabilityStatus.BLOCKED  # 160 mL can never come out of one 100 mL package


def test_exact_decimal_arithmetic_no_epsilon():
    pure = lambda q: [_pure("A", _Q(q, "mL"))]  # noqa: E731
    assert _status([_req("A", QuantityDemand.combine([_Q("0.1", "mL"), _Q("0.2", "mL")]).known)],
                   pure("0.3")) is CapabilityStatus.FIT
    assert _status([_req("A", QuantityDemand.combine([_Q("10.00002", "mL"), _Q("10.00002", "mL")]).known)],
                   pure("20")) is CapabilityStatus.BLOCKED
    assert _status([_req("A", [("mL", "20.0000000005")])], pure("20")) is CapabilityStatus.BLOCKED
    assert _status([_req("A", [("mL", "1e-10")])], pure("5e-10")) is CapabilityStatus.FIT
    assert _status([_req("A", [("mL", "5e-10")])], pure("1e-12")) is CapabilityStatus.BLOCKED


def test_a_species_at_unknown_fraction_is_not_a_proven_draw():
    mix = _bottle("mix", (MaterialComponent.unknown_fraction("A", "impurity?"),
                          MaterialComponent.known("B", "active", 0.0, 1.0)), _Q("10", "mL"))
    assert _status([_req("A", [("mL", "10")])], [mix]) is CapabilityStatus.UNKNOWN


def test_greedy_trap_is_solved_by_max_flow():
    x = _bottle("x", (_ud("A", "0.5", "0.5", "a"), _ud("B", "0.5", "0.5", "b")), _Q("80", "mL"), states=_SOLUTION_STOCK)
    y = _bottle("y", (_ud("B", "0.5", "0.5", "b"),), _Q("80", "mL"), states=_SOLUTION_STOCK)
    reqs = [_req("A", [("mL", "80")], spec=_SOLUTION_REQ), _req("B", [("mL", "80")], spec=_SOLUTION_REQ)]
    assert _status(reqs, [x, y]) is CapabilityStatus.FIT


# =============================================================================================================
# D3-D6 consumption -- the comparison law reaches the material axis
# =============================================================================================================

def test_f69_unresolved_formulation_term_projects_and_is_unknown(iso_route):
    def op_fn(op):
        return dataclasses.replace(op, material_uses=tuple(
            dataclasses.replace(u, formulation="fuming", specification=None)
            if u.role is ProcedureMaterialRole.CATALYST else u for u in op.material_uses))
    route = _rebuild(iso_route, lambda e: _map_ops(e, op_fn))
    req = compile_capability_requirements(route)
    catalyst = next(m for m in req.material if "CATALYST" in m.role)
    assert catalyst.specification.unresolved_terms == ("fuming",)
    pure = _bottle("cat", (MaterialComponent.of_molecule(catalyst.identity, "active", 1.0, 1.0),), _Q("100", "mL"))
    assert _status([catalyst], [pure]) is CapabilityStatus.UNKNOWN


def test_m70_unknown_basis_percent_is_unknown():
    spec = MaterialSpecification(composition=CompositionConstraint(
        "0.05", "0.05", ConcentrationBasis.UNKNOWN, Tolerance.NOMINAL_UNSTATED_TOLERANCE, EvidenceKind.SOURCE_QUOTED))
    comp = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "S", "active", 0.05, 0.05, ConcentrationBasis.MASS_FRACTION)
    bottle = _bottle("s5", (comp,), _Q("100", "mL"), phase=Phase.AQUEOUS_SOLUTION)
    assert _status([_req("S", [("mL", "50")], spec=spec)], [bottle]) is CapabilityStatus.UNKNOWN


def test_m71_assumed_only_agreement_is_unknown_never_fit():
    assumed_req = MaterialSpecification(states=(StateClaim(DilutionState.SOLUTION, EvidenceKind.ASSUMED),))
    certified = _bottle("s", (_ud("S", "0.2", "0.2", "a"),), _Q("100", "mL"), states=_SOLUTION_STOCK)
    assert _status([_req("S", [("mL", "50")], spec=assumed_req)], [certified]) is CapabilityStatus.UNKNOWN
    assumed_stock = _bottle("s", (_ud("S", "0.2", "0.2", "a"),), _Q("100", "mL"),
                            states=(StateClaim(DilutionState.SOLUTION, EvidenceKind.ASSUMED),))
    assert _status([_req("S", [("mL", "50")], spec=_SOLUTION_REQ)], [assumed_stock]) is CapabilityStatus.UNKNOWN
    # control: certified on both sides -> FIT
    assert _status([_req("S", [("mL", "50")], spec=_SOLUTION_REQ)], [certified]) is CapabilityStatus.FIT


def test_phase_is_read_only_from_the_use_and_mismatch_blocks():
    liquid = _pure("A", _Q("100", "mL"))
    assert _status([_req("A", [("mL", "10")], phase=Phase.SOLID)], [liquid]) is CapabilityStatus.BLOCKED
    unknown_phase = _bottle("u", (MaterialComponent.known("A", "a", 1.0, 1.0),), _Q("100", "mL"), phase=Phase.UNKNOWN)
    assert _status([_req("A", [("mL", "10")], phase=Phase.LIQUID)], [unknown_phase]) is CapabilityStatus.UNKNOWN


# =============================================================================================================
# D10 -- process declaration state; D13 monetary
# =============================================================================================================

#: X-high D15: a FULLY declared step (the attention/agitation/active dimensions stated) and a bench declaring every
#: non-time dimension, so these rows isolate the D10 TIME-dimension declaration law alone.
_TIMED = ProcessRequirements(elapsed_minutes=Interval(10.0, 20.0, "min"), workup_included=True,
                             active_minutes=Interval(0.0, 5.0, "min"), attention=Attention.PASSIVE,
                             agitation=Agitation.NONE, provenance="fixture: a sourced 10-20 min step")
_NON_TIME = dict(max_active_minutes=60.0, allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                 allowed_agitation=tuple(Agitation))


@pytest.mark.parametrize("no_limit, time_bounds, expected", [
    (frozenset(), {}, CapabilityStatus.UNKNOWN),
    (frozenset({"max_step_minutes", "max_total_minutes"}), {}, CapabilityStatus.FIT),
    (frozenset({"max_step_minutes"}), {}, CapabilityStatus.UNKNOWN),
    (frozenset({"max_total_minutes"}), {"max_step_minutes": 60.0}, CapabilityStatus.FIT),
    (frozenset(), {"max_step_minutes": 60.0}, CapabilityStatus.UNKNOWN),
    (frozenset({"max_total_minutes"}), {"max_step_minutes": 5.0}, CapabilityStatus.BLOCKED),
])
def test_d10_process_time_dimensions_read_the_declaration_state(no_limit, time_bounds, expected):
    bounds = ProcessBounds.of(**_NON_TIME, **time_bounds)
    a = assess(_profile(process_bounds=bounds, no_limit_dimensions=no_limit), _reqs(process=(_TIMED,)),
               _ps_readiness())
    assert a.process.status is expected, a.process.reasons
    if expected is CapabilityStatus.FIT:
        assert "operator NO_LIMIT preference, not measured capability" in " ".join(a.process.reasons)


def test_d10_no_limit_never_launders_an_undeclared_step():
    a = assess(_profile(no_limit_dimensions=frozenset({"max_step_minutes", "max_total_minutes"})),
               _reqs(process=(_TIMED, None)), _ps_readiness())
    assert a.process.status is CapabilityStatus.UNKNOWN


def test_d13_monetary_undeclared_budget_is_unknown_and_no_limit_is_a_tagged_fit():
    assert assess(_profile(), _reqs(), _ps_readiness()).monetary.status is CapabilityStatus.UNKNOWN
    a = assess(_profile(no_limit_dimensions=frozenset({"budget"})), _reqs(), _ps_readiness())
    assert a.monetary.status is CapabilityStatus.FIT
    assert "NO_LIMIT" in " ".join(a.monetary.reasons)


def test_assessment_records_its_readiness_and_the_bumped_schema():
    readiness = _ps_readiness()
    a = assess(_profile(), _reqs(), readiness)
    assert a.schema_version == CAPABILITY_ASSESSMENT_SCHEMA == "smartchem.capability/capability-assessment-v1alpha2"
    assert a.readiness_tier == readiness.tier == "PROCESS_SPECIFIED"
    assert a.readiness_digest == readiness.digest


# =============================================================================================================
# D13 -- Lane G structure-theorem regression fixtures (each reproduced overall CAPABILITY_FIT at 4b8f8c2)
# =============================================================================================================

_ELAPSED = (lambda e: dataclasses.replace(e, process=dataclasses.replace(  # noqa: E731
    e.process, elapsed_minutes=Interval(60.0, 240.0, "min"))))


def _k2_op(op):
    if op.ordinal == 1:
        return dataclasses.replace(op, material_uses=tuple(
            u for u in op.material_uses if u.role is not ProcedureMaterialRole.SUBSTRATE))
    return dataclasses.replace(op, material_uses=())


def test_lane_g_k1b_empty_typed_uses_is_not_fit_and_its_control_is_not_fit(iso_route):
    inv = (household_white_vinegar(), _pick("isoamyl"))
    stripped = _rebuild(iso_route, lambda e: _map_ops(_ELAPSED(e), lambda op: dataclasses.replace(op, material_uses=())))
    req = compile_capability_requirements(stripped)
    untyped = [m for m in req.material if m.untyped_source_text]
    assert {m.name for m in untyped} >= {"acetic acid", "sulfuric acid", "magnesium sulfate"}
    a = assess(isopentyl_capability_fit_bench(material_inventory=inv), req, evaluate_route(stripped))
    assert a.material.status is CapabilityStatus.UNKNOWN
    assert a.overall is not CapabilityStatus.FIT
    control = _rebuild(iso_route, _ELAPSED)
    c = assess(isopentyl_capability_fit_bench(material_inventory=inv), compile_capability_requirements(control),
               evaluate_route(control))
    assert c.overall is not CapabilityStatus.FIT


def test_lane_g_k2_partial_typing_is_not_fit(iso_route):
    route = _rebuild(iso_route, lambda e: _map_ops(_ELAPSED(e), _k2_op))
    inv = (_pick("glacial"), _pick("sulfuric"), _pick("isoamyl"))
    req = compile_capability_requirements(route)
    a = assess(isopentyl_capability_fit_bench(material_inventory=inv), req, evaluate_route(route))
    assert a.material.status is not CapabilityStatus.FIT
    assert a.overall is not CapabilityStatus.FIT
    # the untyped alcohol + workup auxiliaries reach the hazard lane too (never silently skipped)
    assert any("untyped source material" in h for h in req.hazard_unresolved)
    # a balanced species with no hazard record is surfaced (parity with the typed path)
    assert any("balanced species" in h for h in req.hazard_unresolved)


def test_lane_g_x1_stated_duration_and_bare_hardware_ops_are_not_fit(iso_route):
    loc = "round-v fixture locator"

    def env(e):
        e = dataclasses.replace(e, duration=Interval(30000.0, 30000.0, "min"), process=dataclasses.replace(
            e.process, elapsed_minutes=Interval(60.0, 240.0, "min"), equipment=None))
        return _map_ops(e, lambda op: _k2_op(dataclasses.replace(
            op, apparatus=(), duration=EvidenceField.present(Interval(30000.0, 30000.0, "min"), loc)
            if op.kind is OperationKind.HOLD else op.duration)))
    route = _rebuild(iso_route, env)
    inv = (_pick("glacial"), _pick("sulfuric"), _pick("isoamyl"))
    bench = isopentyl_capability_fit_bench(material_inventory=inv, equipment=frozenset(), measurement=frozenset())
    req = compile_capability_requirements(route)
    a = assess(bench, req, evaluate_route(route))
    assert a.process.status is CapabilityStatus.UNKNOWN
    assert any("30000 min" in u for u in req.process_unresolved)
    assert a.equipment.status is not CapabilityStatus.NOT_APPLICABLE
    assert a.equipment.status is not CapabilityStatus.FIT
    assert a.measurement.status is CapabilityStatus.UNKNOWN
    assert a.overall is not CapabilityStatus.FIT


def test_lane_g_x2_envelope_temperature_and_pressure_reach_the_physical_axis(iso_route):
    def env(e):
        e = dataclasses.replace(e, temperature=Interval(298.0, 600.0, "K"), pressure=Interval(50.0, 50.0, "atm"),
                                process=dataclasses.replace(e.process, elapsed_minutes=Interval(60.0, 240.0, "min")))
        return _map_ops(e, _k2_op)
    route = _rebuild(iso_route, env)
    req = compile_capability_requirements(route)
    assert req.physical.max_temperature_k == 600.0 and req.physical.max_pressure_atm == 50.0
    bench = _open_bench((_pick("glacial"), _pick("sulfuric"), _pick("isoamyl")),
                        physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, max_pressure_atm=2.0,
                                                          min_pressure_atm=1.0),
                        process_bounds=_bench_process_bounds())
    a = assess(bench, req, evaluate_route(route))
    assert a.physical.status is CapabilityStatus.BLOCKED
    assert a.overall is CapabilityStatus.BLOCKED


def test_lane_g_applied_field_and_non_kelvin_op_temperature_fail_closed(iso_route):
    loc = "round-v fixture locator"

    def env(e):
        e = dataclasses.replace(e, applied_field="microwave irradiation")
        return _map_ops(e, lambda op: dataclasses.replace(
            op, temperature=EvidenceField.present(Interval(100.0, 120.0, "C"), loc))
            if op.kind is OperationKind.HOLD else op)
    req = compile_capability_requirements(_rebuild(iso_route, env))
    assert any("applied field" in u for u in req.equipment_unrecognized)
    assert any("'C'" in u for u in req.physical_unresolved)
    a = assess(_profile(physical_bounds=PhysicalBounds.of(max_temperature_k=999.0, max_pressure_atm=9.0,
                                                          min_pressure_atm=0.5)), req, _ps_readiness())
    assert a.physical.status is CapabilityStatus.UNKNOWN


def test_lane_g_f1_commodity_lead_and_f2_dilute_bottle_are_never_proven_draws():
    acid = _mol("acetic acid")
    lead = stock_material_from_commodity(commodity_for(acid))
    need = _req("acetic acid", [("mL", "20")], identity=acid)
    assert _status([need], [lead]) is CapabilityStatus.UNKNOWN
    vinegar = _bottle("vinegar-25mL", (MaterialComponent.of_molecule(acid, "active", 0.04, 0.06),
                                       MaterialComponent.known("water", "solvent", 0.94, 0.96)),
                      _Q("25", "mL"), phase=Phase.AQUEOUS_SOLUTION)
    assert _status([need], [vinegar]) is CapabilityStatus.UNKNOWN


def test_procurement_reads_typed_catalyst_uses_too(iso_route):
    def env(e):
        return dataclasses.replace(e, catalysts=())
    req = compile_capability_requirements(_rebuild(iso_route, env))
    assert [name for name, _ in req.procurement_catalysts] == ["sulfuric acid"]


# =============================================================================================================
# the grep law: no formulation vocabulary, no reagent identities in the compiler/assessor
# =============================================================================================================

_BANNED = (
    "glacial", "conc", "concentrated", "anhydrous", "saturated", "neat", "aqueous", "fuming", "absolute",
    "acetic", "isoamyl", "isopentyl", "sulfuric", "sulphuric", "bicarbonate", "sodium", "magnesium",
    "chloride", "sulfate", "vinegar", "brine", "water", "ethanol", "methanol", "hydrochloric",
    "H2SO4", "HCl", "NaHCO3", "NaCl", "MgSO4",
)


@pytest.mark.parametrize("module", ["requirements.py", "assess.py", "quantity.py"])
def test_the_capability_core_contains_no_formulation_vocabulary_or_reagent_identity(module):
    src = (pathlib.Path(__file__).resolve().parents[1] / "smartchem" / "capability" / module).read_text()
    # X-high: an identifier character (``_``) is part of the word -- ``EquipmentCapability.WATER_BATH`` is a closed
    # EQUIPMENT vocabulary member (D16's kind-admissibility table), not the reagent word "water".
    hits = sorted({w for w in _BANNED if re.search(rf"(?<![A-Za-z_]){re.escape(w)}(?![A-Za-z_])", src, re.I)})
    assert hits == [], f"{module} carries formulation/reagent words: {hits}"
