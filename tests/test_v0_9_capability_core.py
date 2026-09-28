"""v0.9 Capability Compiler -- Round II core (Wave B item 1, "v09-capability-core") pure unit tests.

**Ooh yeah, testing time!** These are the receipts that this Meeseeks actually did the job the FREEZE
contract (``docs/research/V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md``) describes, not just
something that imports cleanly. Every test here is a PURE unit test: no network, no service layer, no
presets (those are a sibling Wave-B file) -- just the closed resolver, the pure requirement projection,
the ``CapabilityProfile`` type, and the pure verdict fold, checked against hand-built fixtures and one
real, source-backed, searched route (isopentyl acetate).
"""
from __future__ import annotations

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import CapabilityAssessment, assess
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    VentilationCapability,
)
from smartchem.capability.equipment_resolver import (
    classify_apparatus_strings,
    resolve_apparatus,
    resolve_apparatus_strings,
)
from smartchem.capability.profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile
from smartchem.capability.quantity import QuantityDemand
from smartchem.capability.requirements import (
    MaterialRequirement,
    RouteCapabilityRequirements,
    WasteRequirement,
    compile_capability_requirements,
)
from smartchem.constraints import PhysicalBounds
from smartchem.data.reagents import Availability, commodity_for
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import CareLevel
from smartchem.experiment.readiness import (
    ObligationStatus,
    RouteReadiness,
    StepReadiness,
    evaluate_route,
)
from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    stock_material_from_commodity,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    EvidenceKind,
    MaterialSpecification,
    Tolerance,
)
from smartchem.process_constraints import ProcessBounds
from smartchem.structure import structure_by_name

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

#: A sourced mass-fraction FLOOR (>= 0.9) on the use's own species -- the Round V replacement for the retired
#: ``required_assay`` float (a typed composition constraint at the evidence origin, never compiler vocabulary).
_FLOOR_90 = MaterialSpecification(composition=CompositionConstraint(
    "0.9", "1", ConcentrationBasis.MASS_FRACTION, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED))
_FLOOR_99 = MaterialSpecification(composition=CompositionConstraint(
    "0.99", "1", ConcentrationBasis.MASS_FRACTION, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED))


# -- shared plumbing: a real, searched, source-backed route (mirrors tests/test_v0_8_procedure_migration.py) ---

def _search(target_name, reagents, have, max_depth):
    target = resolve_target(target_name, InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_route():
    """The real, LibreTexts-sourced isopentyl-acetate esterification route -- PROCESS_SPECIFIED tier,
    with a typed ``ProcedureEvidence`` naming a reflux condenser and a distillation rig."""
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


# -- shared plumbing: minimal hand-built fixtures, so the fold tests never need a real search ------------------

def _molecule(name: str):
    return structure_by_name(name).molecule


def _pass_step_readiness() -> StepReadiness:
    """A fully-discharged step -- tier PROCESS_SPECIFIED."""
    return StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED,
        reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="test-fixture-reaction",
        conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.SATISFIED,
        workup_isolation=ObligationStatus.SATISFIED,
        provenance=("https://example.test/fixture",),
        open_obligations=(),
    )


def _process_specified_route_readiness() -> RouteReadiness:
    return RouteReadiness(per_step=(_pass_step_readiness(),), route_open_obligations=())


def _reaction_vouched_route_readiness() -> RouteReadiness:
    """A step whose reaction type is recognized but whose conditions are not sourced -- tier
    REACTION_VOUCHED, strictly below PROCESS_SPECIFIED."""
    reason = "conditions: declared but not backed by an accepted source citation"
    step = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED,
        reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="test-fixture-reaction",
        conditions=ObligationStatus.UNSATISFIED,
        process=ObligationStatus.UNKNOWN,
        workup_isolation=ObligationStatus.UNKNOWN,
        provenance=(),
        open_obligations=(reason,),
    )
    assert step.tier == "REACTION_VOUCHED"
    return RouteReadiness(per_step=(step,), route_open_obligations=(reason,))


def _empty_requirements(
    *,
    material=(),
    equipment=frozenset(),
    equipment_unrecognized=(),
    physical=None,
    process=(None,),
    containment=frozenset(),
    containment_reasons=(),
    hazard_unresolved=(),
    measurement=frozenset(),
    measurement_unrecognized=(),
    waste=None,
    procurement_catalysts=(),
    attention_care=CareLevel.UNKNOWN,
    monetary=None,
) -> RouteCapabilityRequirements:
    return RouteCapabilityRequirements(
        route_digest="test-fixture-route-digest",
        material=material,
        equipment=equipment,
        equipment_unrecognized=equipment_unrecognized,
        physical=physical if physical is not None else PhysicalBounds.unconstrained(),
        process=process,
        containment=containment,
        containment_reasons=containment_reasons,
        hazard_unresolved=hazard_unresolved,
        measurement=measurement,
        measurement_unrecognized=measurement_unrecognized,
        waste=waste if waste is not None else WasteRequirement(frozenset(), ()),
        procurement_catalysts=procurement_catalysts,
        attention_care=attention_care,
        monetary=monetary if monetary is not None else CostVector(),
    )


def _empty_profile(
    *,
    material_inventory=(),
    equipment=frozenset(),
    physical_bounds=None,
    process_bounds=None,
    containment=frozenset(),
    ventilation=frozenset(),
    measurement=frozenset(),
    waste_handling=frozenset(),
    procurement=frozenset(),
    budget=None,
    no_limit_dimensions=frozenset(),
) -> CapabilityProfile:
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id="test-fixture-profile",
        material_inventory=material_inventory,
        equipment=equipment,
        physical_bounds=physical_bounds if physical_bounds is not None else PhysicalBounds.unconstrained(),
        process_bounds=process_bounds if process_bounds is not None else ProcessBounds.unconstrained(),
        containment=containment,
        ventilation=ventilation,
        measurement=measurement,
        waste_handling=waste_handling,
        procurement=procurement,
        budget=budget,
        provenance="pure unit-test fixture, not a real declared bench",
        no_limit_dimensions=no_limit_dimensions,
    )


#: Round V D13: an undeclared budget is UNKNOWN against any route. The pure fold tests below that exercise the
#: FIT branch declare the explicit operator NO_LIMIT budget preference -- the only way an absent budget passes.
_NO_LIMIT_BUDGET = frozenset({"budget"})


# -- 1. the closed apparatus resolver -------------------------------------------------------------------------

def test_resolver_recognizes_the_forced_corpus_apparatus_strings():
    assert resolve_apparatus("Buchner funnel") is EquipmentCapability.VACUUM_FILTRATION
    assert resolve_apparatus("reflux condenser") is EquipmentCapability.REFLUX_CONDENSER
    assert resolve_apparatus("distillation apparatus") is EquipmentCapability.FRACTIONAL_DISTILLATION
    assert resolve_apparatus("thermometer") is EquipmentCapability.THERMOMETER
    # normalization (whitespace/case) is not fuzziness: the SAME apparatus, differently quoted, still resolves.
    assert resolve_apparatus("  Reflux   Condenser ") is EquipmentCapability.REFLUX_CONDENSER


def test_resolver_unrecognized_apparatus_string_is_unknown_never_a_guess():
    # a real corpus consumable that is NOT tracked equipment
    assert resolve_apparatus("boiling stones") is None
    # a never-seen string
    assert resolve_apparatus("a completely novel piece of glassware") is None
    # NO fuzzy substring matching: containing "distill" must not borrow FRACTIONAL_DISTILLATION (kills M5)
    assert resolve_apparatus("a distillation-adjacent gadget nobody taught this table") is None


def test_resolve_apparatus_strings_partitions_recognized_from_unresolved():
    recognized, unresolved = resolve_apparatus_strings(
        ["reflux condenser", "boiling stones", "heating mantle", "glass rod"]
    )
    assert recognized == frozenset({EquipmentCapability.REFLUX_CONDENSER, EquipmentCapability.CONTROLLED_HEATING})
    assert unresolved == frozenset({"boiling stones", "glass rod"})


def test_classify_apparatus_strings_separates_vetted_consumables_from_genuinely_unrecognized():
    """The three-way cut ``resolve_apparatus_strings`` never made: a vetted whitelisted consumable
    ("boiling stones") and a string the resolver has simply never met ("rotary evaporator") must land in
    two DIFFERENT groups -- conflating them is exactly the false-FIT hole this excision closes."""
    recognized, ignored, unrecognized = classify_apparatus_strings(
        ["reflux condenser", "boiling stones", "heating mantle", "rotary evaporator"]
    )
    assert recognized == frozenset({EquipmentCapability.REFLUX_CONDENSER, EquipmentCapability.CONTROLLED_HEATING})
    assert ignored == frozenset({"boiling stones"})
    assert unrecognized == frozenset({"rotary evaporator"})


# -- 2. MaterialRequirement assessed via StockMaterial.satisfies (through assess()'s material axis) -----------

def test_material_same_formula_isomer_never_satisfies():
    """(a) A same-formula CONSTITUTIONAL isomer (dimethyl ether, C2H6O) never borrows ethanol's (also
    C2H6O) assay -- IDENTITY_ABSENT is a provable negative, so this is BLOCKED, not a guess."""
    ethanol = _molecule("ethanol")
    dimethyl_ether = _molecule("dimethyl ether")
    assert ethanol.formula == dimethyl_ether.formula  # same formula, different connectivity -- the whole point
    stock = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "stock-dme", "Dimethyl ether, pure",
        (MaterialComponent.of_molecule(dimethyl_ether, "active", 1.0, 1.0),),
        Phase.GAS, "test fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, phase=None, quantity=QuantityDemand.unstated(),
        role="reactant", evidence_source="test fixture",
    )
    profile = _empty_profile(material_inventory=(stock,))
    assessment = assess(profile, _empty_requirements(material=(requirement,)), _process_specified_route_readiness())
    assert assessment.material.status is CapabilityStatus.BLOCKED


def test_material_unknown_assay_is_unknown_never_fit():
    """(b) A material whose active fraction is genuinely UNKNOWN (the honest [0, 1] interval) can never
    certify FIT -- the interval straddles any real assay bar, so the verdict is UNKNOWN, not a guess."""
    ethanol = _molecule("ethanol")
    stock = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "stock-ethanol-unknown", "Ethanol, unspecified purity",
        (MaterialComponent.unknown_molecule(ethanol, "active"),),
        Phase.LIQUID, "test fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, phase=None, quantity=QuantityDemand((("mL", "10"),), 0),
        role="reactant", evidence_source="test fixture", specification=_FLOOR_90,
    )
    profile = _empty_profile(material_inventory=(stock,))
    assessment = assess(profile, _empty_requirements(material=(requirement,)), _process_specified_route_readiness())
    assert assessment.material.status is CapabilityStatus.UNKNOWN


def test_material_commodity_unknown_fraction_is_unknown():
    """(c) A commodity SOURCE LEAD (stock_material_from_commodity's bridge) is an UNKNOWN-fraction
    material by construction (section 10.1) -- it can never satisfy a pure-reagent requirement, so a
    household commodity never launders into a FIT."""
    acetic_acid = _molecule("acetic acid")
    commodity = commodity_for(acetic_acid)
    assert commodity is not None
    stock = stock_material_from_commodity(commodity)
    requirement = MaterialRequirement(
        identity=acetic_acid, phase=None, quantity=QuantityDemand((("mL", "10"),), 0),
        role="reactant", evidence_source="test fixture", specification=_FLOOR_99,
    )
    profile = _empty_profile(material_inventory=(stock,))
    assessment = assess(profile, _empty_requirements(material=(requirement,)), _process_specified_route_readiness())
    assert assessment.material.status is CapabilityStatus.UNKNOWN


def test_material_empty_inventory_is_unknown_not_fit():
    """An empty ``material_inventory`` (the honest ResearchLab-with-no-declared-stock default, F2) is
    UNKNOWN by construction -- never a vacuous FIT over an empty pantry."""
    ethanol = _molecule("ethanol")
    requirement = MaterialRequirement(
        identity=ethanol, phase=None, quantity=QuantityDemand.unstated(),
        role="reactant", evidence_source="test fixture",
    )
    profile = _empty_profile()  # material_inventory=() default
    assessment = assess(profile, _empty_requirements(material=(requirement,)), _process_specified_route_readiness())
    assert assessment.material.status is CapabilityStatus.UNKNOWN


def test_material_possession_alone_is_never_fit_but_an_exact_draw_of_a_provably_pure_bottle_is():
    """Round V (D1/D2/D13 P0-3) -- FLIPPED from Round IV's "FIT by possession". Possession is not a capability:

    * an ``UNKNOWN`` quantity (a real, positive, unsized demand) is never FIT, whatever the bottle;
    * an EXACT 50 mL demand with an EMPTY specification against a bottle of UNKNOWN amount is UNKNOWN (G- capacity 0);
    * the same EXACT demand against a declared 100 mL bottle whose species' LOWER fraction is exactly 1 (provably the
      pure species, so drawing 50 mL of it IS 50 mL of the species) is FIT -- a proven, commensurable allocation.
    """
    ethanol = _molecule("ethanol")

    def _user_declared_fraction(lo, hi):
        from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
        from smartchem.material_spec import ConcentrationBasis, EvidenceKind
        return IntervalEvidence.build(
            kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
            inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                    TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
            domain_of_validity="test fixture: the operator's own bottle")

    def _bottle(quantity):
        return StockMaterial(
            STOCK_MATERIAL_SCHEMA, "stock-ethanol-pure", "Ethanol, ACS reagent grade",
            # Wave-C K2: "provably pure" needs a fraction basis + CERTIFYING evidence, not a bare 1.0
            (MaterialComponent.evidenced(ethanol, "active", _user_declared_fraction("1", "1")),),
            Phase.LIQUID, "test fixture", quantity=quantity,
        )

    exact = MaterialRequirement(
        identity=ethanol, phase=None, quantity=QuantityDemand((("mL", "50"),), 0),
        role="reactant", evidence_source="test fixture: no sourced purity spec",
    )
    unsized = MaterialRequirement(
        identity=ethanol, phase=None, quantity=QuantityDemand.unstated(),
        role="reactant", evidence_source="test fixture: no sourced quantity",
    )
    from smartchem.experiment.stock import StockQuantity

    def _material(req, bottle):
        return assess(_empty_profile(material_inventory=(bottle,)), _empty_requirements(material=(req,)),
                      _process_specified_route_readiness()).material

    assert _material(unsized, _bottle(StockQuantity.of("1000", "mL"))).status is CapabilityStatus.UNKNOWN
    assert _material(exact, _bottle(None)).status is CapabilityStatus.UNKNOWN
    fit = _material(exact, _bottle(StockQuantity.of("100", "mL")))
    assert fit.status is CapabilityStatus.FIT
    assert "EXACT 50 mL" in " ".join(fit.reasons)


# -- 3. compile_capability_requirements on the real isopentyl-acetate route ------------------------------------

def test_compile_capability_requirements_equipment_axis_reads_apparatus_not_equipment_for_step():
    """F1's whole point: ``equipment_for_step`` silently drops the reflux condenser and the distillation
    rig this source names. The compiled REQUIREMENT must contain both -- proof it read the sourced
    ``ProcedureEvidence.apparatus``/``ProcessRequirements.equipment`` tuples instead."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    assert EquipmentCapability.FRACTIONAL_DISTILLATION in requirements.equipment
    assert EquipmentCapability.REFLUX_CONDENSER in requirements.equipment
    assert EquipmentCapability.SEPARATORY_FUNNEL in requirements.equipment
    # the corpus consumable "boiling stones" is real evidence but a vetted, whitelisted consumable -- it is
    # dropped, not carried as unrecognized; it must never invent a phantom EquipmentCapability member.
    assert "boiling stones" not in requirements.equipment_unrecognized
    # Round V D13 (FLIPPED from ``== ()``): the only remainder is the UNREAD hardware demand of the two ops the
    # source leaves without apparatus (cool; dry) -- never an untabled apparatus string.
    assert requirements.equipment_unrecognized == (
        "step 1 op 3 COOL states no apparatus", "step 1 op 8 DRY states no apparatus")


def test_compile_capability_requirements_is_a_pure_function_of_the_route_alone():
    """Calling it twice on routes built from the SAME search yields byte-identical requirements -- no
    hidden profile/global-state dependency (decision 2: "the compiler NEVER reads a CapabilityProfile")."""
    route_a = _isopentyl_route()
    route_b = _isopentyl_route()
    assert compile_capability_requirements(route_a).digest == compile_capability_requirements(route_b).digest


# -- 3b. the equipment axis's fail-closed gate on a genuinely-unrecognized apparatus string --------------------
# (FREEZE decision 4: "unrecognized apparatus -> UNKNOWN, never silently satisfied" -- this was the exact hole
# left open when the equipment axis only ever checked the RECOGNIZED set and never looked at what fell through.)

_ALL_EQUIPMENT_CAPABILITIES = frozenset(EquipmentCapability)


def test_equipment_axis_is_unknown_when_a_genuinely_unrecognized_apparatus_string_is_carried():
    """A synthetic requirement carrying an apparatus string the closed resolver has NEVER met (a "rotary
    evaporator") must cap the equipment axis at UNKNOWN, even against a profile that owns EVERY single
    EquipmentCapability member -- an untabled capability item is an open question, never a silent FIT by
    omission (the exact false-FIT this gate exists to refuse)."""
    requirements = _empty_requirements(
        equipment=frozenset({EquipmentCapability.REFLUX_CONDENSER}),
        equipment_unrecognized=("rotary evaporator",),
    )
    profile = _empty_profile(equipment=_ALL_EQUIPMENT_CAPABILITIES)
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.equipment.status is CapabilityStatus.UNKNOWN
    assert "rotary evaporator" in " ".join(assessment.equipment.reasons)


def test_the_real_isopentyl_route_equipment_axis_is_unknown_on_its_unread_hardware_ops():
    """Round V D13 -- FLIPPED from "equipment FIT against a maximal bench". The source's cool and dry operations name
    no apparatus; a demand stated anywhere must reach its axis or that axis fails closed, so even a profile owning
    EVERY EquipmentCapability is UNKNOWN on equipment (never FIT by omission) -- while the recognized set itself is
    still fully covered (no provable block)."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = _empty_profile(equipment=_ALL_EQUIPMENT_CAPABILITIES)
    assessment = assess(profile, requirements, evaluate_route(route))
    assert assessment.equipment.status is CapabilityStatus.UNKNOWN
    joined = " ".join(assessment.equipment.reasons)
    assert "COOL states no apparatus" in joined and "covers every required capability" in joined


# -- 4. the verdict fold ----------------------------------------------------------------------------------------

def test_verdict_fold_blocked_beats_unknown_beats_fit():
    """A route with BOTH a BLOCKED equipment axis (profile lacks a required capability) AND an UNKNOWN
    material axis (empty inventory) must fold to BLOCKED overall -- BLOCKED strictly outranks UNKNOWN."""
    ethanol = _molecule("ethanol")
    requirements = _empty_requirements(
        equipment=frozenset({EquipmentCapability.FRACTIONAL_DISTILLATION}),
        material=(MaterialRequirement(
            identity=ethanol, phase=None, quantity=QuantityDemand.unstated(),
            role="reactant", evidence_source="test fixture",
        ),),
    )
    profile = _empty_profile(equipment=frozenset())  # missing FRACTIONAL_DISTILLATION; no material inventory
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.equipment.status is CapabilityStatus.BLOCKED
    assert assessment.material.status is CapabilityStatus.UNKNOWN
    assert assessment.overall is CapabilityStatus.BLOCKED


def test_verdict_fold_unknown_beats_fit():
    """An UNKNOWN axis with every other axis FIT/NOT_APPLICABLE/UNCONSTRAINED still folds to UNKNOWN
    overall -- an open question is never silently rounded up to FIT."""
    ethanol = _molecule("ethanol")
    requirements = _empty_requirements(
        material=(MaterialRequirement(
            identity=ethanol, phase=None, quantity=QuantityDemand.unstated(),
            role="reactant", evidence_source="test fixture",
        ),),
    )
    profile = _empty_profile()  # empty inventory -> material UNKNOWN; every other axis NOT_APPLICABLE/UNCONSTRAINED
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.material.status is CapabilityStatus.UNKNOWN
    assert all(
        axis.status is not CapabilityStatus.BLOCKED
        for axis in assessment.axes
    )
    assert assessment.overall is CapabilityStatus.UNKNOWN


def test_verdict_fold_tier_below_process_specified_can_never_be_overall_fit():
    """HARD LAW (decision 5): even when every axis is FIT/NOT_APPLICABLE/UNCONSTRAINED, a route readiness
    tier below PROCESS_SPECIFIED caps the overall verdict at UNKNOWN -- it can never reach FIT."""
    requirements = _empty_requirements()  # every axis NOT_APPLICABLE/UNCONSTRAINED (monetary: NO_LIMIT FIT)
    profile = _empty_profile(no_limit_dimensions=_NO_LIMIT_BUDGET)
    assessment = assess(profile, requirements, _reaction_vouched_route_readiness())
    assert all(
        axis.status in (CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED, CapabilityStatus.FIT)
        for axis in assessment.axes
    )
    assert assessment.overall is CapabilityStatus.UNKNOWN
    assert assessment.readiness_tier == "REACTION_VOUCHED"


def test_verdict_fold_reaches_fit_when_tier_is_process_specified_and_nothing_is_blocked_or_unknown():
    """The other side of the HARD LAW: a PROCESS_SPECIFIED-or-higher tier with every axis FIT/
    NOT_APPLICABLE/UNCONSTRAINED DOES reach overall FIT. (This fixture's requirements are trivially empty
    -- a genuine end-to-end material-FIT demonstration on a real route is the forcing-corpus fixture a
    LATER Wave-B item owns, per FREEZE decision 8 item 5; this only proves the fold's positive branch.)"""
    requirements = _empty_requirements()
    profile = _empty_profile(no_limit_dimensions=_NO_LIMIT_BUDGET)
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.overall is CapabilityStatus.FIT
    assert "NO_LIMIT" in " ".join(assessment.monetary.reasons)
    # D13: without the explicit NO_LIMIT preference an undeclared budget is UNKNOWN, never a silent pass.
    assert assess(_empty_profile(), requirements, _process_specified_route_readiness()).overall is (
        CapabilityStatus.UNKNOWN)


def test_profile_missing_fractional_distillation_blocks_the_real_isopentyl_equipment_axis():
    """The explicit gate: a PoorMan-shaped profile (FREEZE decision 6 -- no REFLUX_CONDENSER, no
    FRACTIONAL_DISTILLATION/SIMPLE_DISTILLATION, no VACUUM_FILTRATION, no BALANCE) assessed against the
    REAL compiled isopentyl-acetate requirement is BLOCKED on equipment, and that BLOCKED wins overall
    even though the route's own readiness tier is PROCESS_SPECIFIED."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    poor_man_equipment = frozenset({
        EquipmentCapability.CONTROLLED_HEATING, EquipmentCapability.WATER_BATH, EquipmentCapability.ICE_BATH,
        EquipmentCapability.REACTION_VESSEL, EquipmentCapability.THERMOMETER,
    })
    profile = _empty_profile(equipment=poor_man_equipment)
    assessment = assess(profile, requirements, evaluate_route(route))
    assert assessment.equipment.status is CapabilityStatus.BLOCKED
    joined_reasons = " ".join(assessment.equipment.reasons)
    assert "FRACTIONAL_DISTILLATION" in joined_reasons
    assert "REFLUX_CONDENSER" in joined_reasons
    assert assessment.overall is CapabilityStatus.BLOCKED


# -- 5. containment: outdoor ventilation never substitutes for a declared containment requirement --------------

def test_outdoor_ventilation_never_satisfies_a_fume_hood_containment_requirement():
    """F-nag / mutation-kill M6: a profile with OUTDOOR ventilation but NO declared FUME_HOOD containment
    must stay BLOCKED against a FUME_HOOD requirement -- ventilation is a real, different axis, and it
    never quietly clears a containment obligation."""
    requirements = _empty_requirements(containment=frozenset({ContainmentCapability.FUME_HOOD}))
    profile = _empty_profile(containment=frozenset(), ventilation=frozenset({VentilationCapability.OUTDOOR}))
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.containment.status is CapabilityStatus.BLOCKED
    assert assessment.overall is CapabilityStatus.BLOCKED


def test_the_real_isopentyl_route_derives_a_fume_hood_containment_requirement():
    """Ties the containment axis back to real evidence: the isopentyl route's acetic acid carries a
    sourced GHS hazard, so ``equipment_for_step`` emits its CONTAINMENT-kind item and the compiled
    requirement names FUME_HOOD -- never derived from the apparatus tuples (F-nag's two-lanes rule)."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    assert requirements.containment == frozenset({ContainmentCapability.FUME_HOOD})


# -- 6. procurement: profile-relative catalyst obtainability (gate #10) -----------------------------------------
# Built DIRECTLY on RouteCapabilityRequirements.procurement_catalysts -- no real route needs to declare a
# catalyst to exercise this axis; the fold under test is entirely inside assess()'s _procurement_axis.

def test_procurement_industrial_catalyst_blocks_under_a_kitchen_profile_but_fits_under_a_lab_that_declares_it():
    """M18's exact shape: a recognized INDUSTRIAL-tier catalyst is BLOCKED against a profile whose
    procurement never reached that tier, and FIT the moment a profile's declared ``procurement`` set
    actually includes INDUSTRIAL -- a lab profile never gets an industrial catalyst for free just because
    it is otherwise well-equipped."""
    requirements = _empty_requirements(procurement_catalysts=(("Pd/C", Availability.INDUSTRIAL),))
    kitchen_profile = _empty_profile(procurement=frozenset({Availability.GROCERY, Availability.HARDWARE}))
    lab_profile = _empty_profile(procurement=frozenset({Availability.HARDWARE, Availability.INDUSTRIAL}),
                                 no_limit_dimensions=_NO_LIMIT_BUDGET)

    blocked = assess(kitchen_profile, requirements, _process_specified_route_readiness())
    assert blocked.procurement.status is CapabilityStatus.BLOCKED
    assert "Pd/C" in " ".join(blocked.procurement.reasons)
    assert blocked.overall is CapabilityStatus.BLOCKED

    fit = assess(lab_profile, requirements, _process_specified_route_readiness())
    assert fit.procurement.status is CapabilityStatus.FIT
    assert fit.overall is CapabilityStatus.FIT


def test_procurement_unrecognized_catalyst_blocks_under_every_profile_even_a_maximal_one():
    """M17's exact shape (the fail-closed law): a declared catalyst this projection could not positively
    classify (``tier is None``) BLOCKS regardless of how permissive ``allowed_tiers`` is -- even a profile
    declaring EVERY ``Availability`` tier never gets to vouch for a substance nobody could identify."""
    requirements = _empty_requirements(procurement_catalysts=(("a mystery catalyst nobody has named before", None),))
    maximal_profile = _empty_profile(procurement=frozenset(Availability))
    assessment = assess(maximal_profile, requirements, _process_specified_route_readiness())
    assert assessment.procurement.status is CapabilityStatus.BLOCKED
    assert "mystery catalyst" in " ".join(assessment.procurement.reasons)
    assert assessment.overall is CapabilityStatus.BLOCKED


def test_procurement_no_declared_catalyst_is_not_applicable():
    """Genuine silence (``catalysts == ()`` on every step) is not a claim either way -- NOT_APPLICABLE,
    never a fabricated FIT and never a fabricated BLOCKED."""
    requirements = _empty_requirements()  # procurement_catalysts=() by default
    profile = _empty_profile(procurement=frozenset(), no_limit_dimensions=_NO_LIMIT_BUDGET)  # NO tiers at all
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.procurement.status is CapabilityStatus.NOT_APPLICABLE
    assert assessment.overall is CapabilityStatus.FIT


def test_procurement_grocery_catalyst_fits_under_the_poor_man_kitchen_tiers():
    """The positive case a poor-man kitchen bench actually needs: a catalyst recognized at GROCERY tier is
    obtainable under the four kitchen-adjacent tiers (mirrors ``catalyst_availability.KITCHEN_TIERS``)."""
    kitchen_tiers = frozenset({
        Availability.GROCERY, Availability.PHARMACY, Availability.HARDWARE, Availability.POOL_GARDEN,
    })
    requirements = _empty_requirements(procurement_catalysts=(("citric acid", Availability.GROCERY),))
    profile = _empty_profile(procurement=kitchen_tiers, no_limit_dimensions=_NO_LIMIT_BUDGET)
    assessment = assess(profile, requirements, _process_specified_route_readiness())
    assert assessment.procurement.status is CapabilityStatus.FIT
    assert assessment.overall is CapabilityStatus.FIT


# -- CapabilityAssessment shape sanity --------------------------------------------------------------------------

def test_capability_assessment_carries_its_profile_and_route_digests():
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = _empty_profile()
    assessment = assess(profile, requirements, evaluate_route(route))
    assert type(assessment) is CapabilityAssessment
    assert assessment.profile_digest == profile.profile_digest
    assert assessment.route_digest == requirements.route_digest == route.digest
    assert assessment.is_capability_assessed is True
    assert assessment.is_capability_fit is (assessment.overall is CapabilityStatus.FIT)
    # D13 P1-4: the readiness the HARD LAW used is part of the verdict's identity.
    readiness = evaluate_route(route)
    assert assessment.readiness_tier == readiness.tier
    assert assessment.readiness_digest == readiness.digest
