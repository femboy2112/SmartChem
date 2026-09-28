"""v0.9 Capability Compiler -- ROUND III forcing matrix + the D1-D9 semantic-hardening receipts.

**LOOK AT ME, I'M THE ACCEPTANCE-ORACLE MEESEEKS!** The Round-III freeze
(``docs/research/V0_9_CAPABILITY_COMPILER_ROUND_III_FREEZE_2026-09-28.md``) ships a forcing matrix that is
the independent oracle: the SAME real, searched routes projected through profiles, and every cell must be
reached HONESTLY -- never a fabricated FIT, never a faked UNKNOWN. This file drives that matrix on the real
searched routes AND pins each frozen decision's discriminator:

* D1/D2/D3/D4 -- source-scoped material law, procedure-only auxiliaries participate, phase/quantity gates.
* D5 -- measurement is live and compared on the SPECIFIC method (IR), never the coarse tier.
* D6 -- an UNCONSTRAINED axis with a real route demand is UNKNOWN, never a free FIT.
* D7 -- a mismatched budget denomination is UNKNOWN, never compared by raw number.
* D8 -- ventilation is a surfaced RESERVED axis; OUTDOOR never clears containment (M6).
* D9 -- a resolved procedure-only hazard (H2SO4 -> H314) forces containment; an unresolvable one is surfaced.

Anti-laundering laws pinned: tier < PROCESS_SPECIFIED never overall FIT; unknown assay/phase/quantity never
FIT; the null route never FITs under any profile.
"""
from __future__ import annotations

import pytest

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import assess
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    WasteCapability,
)
from smartchem.capability.presets import (
    custom,
    isopentyl_capability_fit_bench,
    poor_man,
    research_lab,
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
from smartchem.data import material_library
from smartchem.data.material_library import household_white_vinegar
from smartchem.data.reagents import Availability
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import CareLevel
from smartchem.experiment.readiness import (
    ObligationStatus,
    RouteReadiness,
    StepReadiness,
    evaluate_route,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.material_spec import MaterialSpecification
from smartchem.process_constraints import Agitation, Attention, ProcessBounds

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

_CLEAN = (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)


# -- shared plumbing ------------------------------------------------------------------------------------------

def _search(target_name, reagents, have, max_depth, tkind=InputKind.NAME):
    target = resolve_target(target_name, tkind).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_route():
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


def _nonclean_axes(assessment):
    """The axis-name -> status map for every axis NOT already FIT/NOT_APPLICABLE/UNCONSTRAINED."""
    named = {
        "material": assessment.material, "equipment": assessment.equipment, "physical": assessment.physical,
        "process": assessment.process, "containment": assessment.containment,
        "ventilation": assessment.ventilation, "measurement": assessment.measurement,
        "waste": assessment.waste, "procurement": assessment.procurement,
        "attention_care": assessment.attention_care, "monetary": assessment.monetary,
    }
    return {k: v.status for k, v in named.items() if v.status not in _CLEAN}


# -- minimal fixtures for axis-level unit tests (no search needed) ---------------------------------------------

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


def _ps_readiness() -> RouteReadiness:
    step = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="fixture", conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.SATISFIED, workup_isolation=ObligationStatus.SATISFIED,
        provenance=("https://example.test/x",), open_obligations=(),
    )
    return RouteReadiness(per_step=(step,), route_open_obligations=())


# =============================================================================================================
# 1. THE ISOPENTYL FORCING-MATRIX ROW (the release headline, on the real searched route)
# =============================================================================================================

def test_matrix_isopentyl_research_lab_no_stock_is_unknown_on_material_and_the_semantic_axes():
    """Round IV: the 'material only' UNKNOWN died with the Round-III FIT. A well-equipped ResearchLab with
    NO declared stock now lands overall UNKNOWN on FOUR axes. material is UNKNOWN (empty pantry, an open
    question); the whole-path semantic hardening adds three that NO bench can clear from this source: process
    UNKNOWN (F56 -- the source times only the 1-hr reflux FLOOR; the untimed workup+distillation elapsed
    CEILING is undeclared, so an unbounded-duration process cannot be certified), containment UNKNOWN (F47 --
    the ionic NaHCO3/NaCl/MgSO4 auxiliaries carry unresolved hazards), waste UNKNOWN (F49 -- the spent
    workup streams have no sourced disposal routing)."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    assert readiness.tier == "PROCESS_SPECIFIED"
    a = assess(research_lab(), req, readiness)
    assert a.overall is CapabilityStatus.UNKNOWN
    # Round V D13 (FLIPPED: +equipment, +monetary): the source's cool/dry ops name no apparatus (equipment
    # UNKNOWN), and research_lab() declares no budget (UNDECLARED, not unconstrained -> monetary UNKNOWN).
    # X-high (FLIPPED: +physical, +measurement): D14 -- the reflux/cool temperatures are prose and the fractional
    # distillation states no typed temperature with no whole-step peak left to cover it (the 416 K head range is a
    # LOWER bound, P-X2); D16 -- the "basic to litmus" / fraction / reflux-time ENDPOINT criteria have no typed
    # measurement carrier. Both are unread demands on their owning axis, never a pass.
    assert _nonclean_axes(a) == {
        "material": CapabilityStatus.UNKNOWN,
        "equipment": CapabilityStatus.UNKNOWN,
        "physical": CapabilityStatus.UNKNOWN,
        "process": CapabilityStatus.UNKNOWN,
        "containment": CapabilityStatus.UNKNOWN,
        "measurement": CapabilityStatus.UNKNOWN,
        "waste": CapabilityStatus.UNKNOWN,
        "monetary": CapabilityStatus.UNKNOWN,
    }


def test_matrix_isopentyl_poor_man_is_blocked_on_equipment_measurement_and_containment():
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    a = assess(poor_man(), req, evaluate_route(route))
    assert a.overall is CapabilityStatus.BLOCKED
    assert a.equipment.status is CapabilityStatus.BLOCKED
    assert "FRACTIONAL_DISTILLATION" in " ".join(a.equipment.reasons)
    assert a.measurement.status is CapabilityStatus.BLOCKED  # no IR
    assert "INFRARED_SPECTROSCOPY" in " ".join(a.measurement.reasons)
    assert a.containment.status is CapabilityStatus.BLOCKED  # no fume hood


def test_matrix_isopentyl_fully_declared_custom_collapses_to_unknown_on_the_semantic_axes():
    """Round IV: the fully-declared Custom bench NO LONGER reaches CAPABILITY_FIT -- this is the honest
    ceiling, not a regression. It is FIT on every RESOURCEABLE axis (material/equipment/physical/measurement/
    procurement), but three whole-path semantic axes collapse to UNKNOWN from the source itself, no matter
    how completely the bench is stocked: process (F56 -- the source times only the 1-hr reflux FLOOR, the
    untimed workup+distillation elapsed CEILING is undeclared), containment (F47 -- the ionic
    NaHCO3/NaCl/MgSO4 auxiliaries carry unresolved hazards), waste (F49 -- the spent workup streams have no
    sourced disposal routing). Overall UNKNOWN, is_capability_fit False. The Round-III FIT rode the
    process-time-omission=unlimited-patience assumption F56 retires; a vanishing positive is scientific
    information -- do NOT restore a FIT by weakening the gate."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    a = assess(isopentyl_capability_fit_bench(), req, evaluate_route(route))
    assert a.overall is CapabilityStatus.UNKNOWN
    assert a.is_capability_fit is False
    # Round V (FLIPPED: +material, +equipment, +monetary): material is UNKNOWN (D2/D13: several requirements have
    # only POSSIBLE sources -- unresolved/unknown-basis specifications, bottles not provably the pure species -- so
    # the proven allocation falls short); equipment UNKNOWN (D13 unread cool/dry ops); monetary UNKNOWN (no budget).
    # X-high (FLIPPED: +physical, +measurement): the same D14 prose/uncovered-thermal-op and D16 endpoint demands as
    # the research-lab row -- no stock or instrument can discharge a demand the source never typed.
    assert _nonclean_axes(a) == {
        "material": CapabilityStatus.UNKNOWN,
        "equipment": CapabilityStatus.UNKNOWN,
        "physical": CapabilityStatus.UNKNOWN,
        "process": CapabilityStatus.UNKNOWN,
        "containment": CapabilityStatus.UNKNOWN,
        "measurement": CapabilityStatus.UNKNOWN,
        "waste": CapabilityStatus.UNKNOWN,
        "monetary": CapabilityStatus.UNKNOWN,
    }


def _vinegar_inventory():
    full = material_library.isopentyl_fully_declared_inventory()
    return tuple(s for s in full if "glacial-acetic" not in s.material_id) + (household_white_vinegar(),)


@pytest.mark.parametrize("label, overrides, axis, expected", [
    ("minus_containment", dict(containment=frozenset()), "containment", CapabilityStatus.BLOCKED),
    ("minus_fractional_distillation",
     dict(equipment=frozenset(EquipmentCapability) - {EquipmentCapability.FRACTIONAL_DISTILLATION}),
     "equipment", CapabilityStatus.BLOCKED),
    ("minus_IR",
     dict(measurement=frozenset({MeasurementMethod.MASS, MeasurementMethod.MELTING_POINT})),
     "measurement", CapabilityStatus.BLOCKED),
    ("insufficient_quantity",
     dict(material_inventory="__insufficient__"), "material", CapabilityStatus.BLOCKED),
    ("minus_procurement", dict(procurement=frozenset()), "procurement", CapabilityStatus.BLOCKED),
])
def test_matrix_isopentyl_targeted_negatives_each_fail_on_their_one_axis(label, overrides, axis, expected):
    """Round IV: each targeted-negative Custom is the fully-declared bench MINUS exactly one capability. The
    cut must BITE -- the TARGET axis goes BLOCKED and the overall verdict is BLOCKED (BLOCKED outranks the
    baseline UNKNOWN axes in the fold). We NO LONGER assert 'every other axis is FIT': that premise died with
    the Round-III positive. The baseline process/containment/waste axes are UNKNOWN on the negatives too
    (F56/F47/F49), so the honest proof is that the removal drives its TARGET axis to BLOCKED and folds the
    whole route to BLOCKED -- not a spurious 'clean single-axis' claim that the vanished FIT once licensed."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    inv = overrides.pop("material_inventory", None)
    if inv == "__insufficient__":
        overrides["material_inventory"] = material_library.isopentyl_insufficient_quantity_inventory()
    a = assess(isopentyl_capability_fit_bench(**overrides), req, evaluate_route(route))
    assert getattr(a, axis).status is expected, (label, _nonclean_axes(a))
    assert a.overall is CapabilityStatus.BLOCKED


@pytest.mark.parametrize("label, inventory", [
    ("wrong_phase", material_library.isopentyl_wrong_phase_inventory),
    ("vinegar", _vinegar_inventory),
])
def test_matrix_isopentyl_uncertifiable_phase_negatives_never_fit(label, inventory):
    """M26 (D4) + the gate-#18 vinegar control. X-high D18 (VERDICT LEGITIMATELY MOVED BLOCKED -> UNKNOWN): both
    BLOCKs rested ONLY on the ungraded phase -- the requirement's LIQUID is an AUTHOR_INFERRED reading (the source
    never states the phase), and an inference can neither certify a match nor refute a mismatch (F71). The
    load-bearing guarantee stays: the substituted bottle is NEVER a FIT, and phase is the named reason."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    a = assess(isopentyl_capability_fit_bench(material_inventory=inventory()), req, evaluate_route(route))
    assert a.material.status is CapabilityStatus.UNKNOWN, label
    assert "phase" in " ".join(a.material.reasons).lower()
    assert a.overall is not CapabilityStatus.FIT and a.is_capability_fit is False


# =============================================================================================================
# 2. THE TIER HARD LAW on the real below-PROCESS_SPECIFIED routes (assessable, NEVER overall FIT)
# =============================================================================================================

def _maximal_bench(profile_id="maximal"):
    return custom(
        profile_id=profile_id, material_inventory=material_library.isopentyl_fully_declared_inventory(),
        equipment=frozenset(EquipmentCapability), containment=frozenset(ContainmentCapability),
        measurement=frozenset(MeasurementMethod), waste_handling=frozenset(WasteCapability),
        procurement=frozenset(Availability),
        physical_bounds=PhysicalBounds.of(max_temperature_k=999.0, max_pressure_atm=99.0),
        process_bounds=ProcessBounds.of(allowed_attention=tuple(Attention), allowed_agitation=tuple(Agitation)),
    )


@pytest.mark.parametrize("target, reagents, have", [
    ("acetylsalicylic acid", ("acetic acid",), ("salicylic acid", "acetic anhydride")),
    ("paracetamol", ("acetic acid",), ("4-aminophenol", "acetic anhydride")),
    ("methyl salicylate", ("water",), ("salicylic acid", "methanol")),
])
def test_below_process_specified_route_never_fits_even_under_a_maximal_bench(target, reagents, have):
    """The tier HARD LAW on the real path: a route below PROCESS_SPECIFIED is ASSESSABLE but can NEVER reach
    overall FIT, even when a maximal bench resources every other axis. UNKNOWN or BLOCKED, never FIT."""
    result = _search(target, reagents, have, 3)
    route = result.routes[0]
    readiness = evaluate_route(route)
    assert readiness.tier != "PROCESS_SPECIFIED"
    a = assess(_maximal_bench(), compile_capability_requirements(route), readiness)
    assert a.is_capability_fit is False
    assert a.overall is not CapabilityStatus.FIT


def test_methyl_salicylate_poor_man_blocks_on_methanol_containment():
    """Matrix row: methyl salicylate under poor_man BLOCKS on containment (methanol's sourced hazard forces a
    fume hood the kitchen lacks) -- and being below PROCESS_SPECIFIED it never FITs regardless."""
    result = _search("methyl salicylate", ("water",), ("salicylic acid", "methanol"), 3)
    route = result.routes[0]
    a = assess(poor_man(), compile_capability_requirements(route), evaluate_route(route))
    assert a.containment.status is CapabilityStatus.BLOCKED
    assert a.overall is CapabilityStatus.BLOCKED


# =============================================================================================================
# 3. THE NULL ROUTE (retro-Diels-Alder, REACTION_VOUCHED): never FIT; the profiles do not launder
# =============================================================================================================

def test_retro_diels_alder_null_route_never_fits_and_does_not_launder():
    """The null case: a REACTION_VOUCHED retro-DA carries no sourced procedure. It can NEVER reach overall
    FIT under ANY profile (tier < PROCESS_SPECIFIED + nothing sourced to project), and the identical
    projection feeds every profile -- research_lab and the fully-declared Custom both land at UNKNOWN
    (gateless, unsourced leaves are an open question, never a provable material negative). Poor_man may
    legitimately BLOCK where a real balanced-species hazard forces containment a kitchen lacks -- honest
    divergence driven by a sourced hazard, NEVER a fabricated FIT."""
    result = _search("C1=CCCCC1", ("C=C",), ("C=CC=C",), 2, tkind=InputKind.SMILES)
    route = result.routes[0]
    readiness = evaluate_route(route)
    assert readiness.tier == "REACTION_VOUCHED"
    req = compile_capability_requirements(route)
    for profile in (research_lab(), poor_man(), isopentyl_capability_fit_bench()):
        a = assess(profile, req, readiness)
        assert a.is_capability_fit is False  # the null route NEVER launders into FIT
    # research_lab() declares NO inventory -> material UNKNOWN (an empty pantry is an open question).
    assert assess(research_lab(), req, readiness).overall is CapabilityStatus.UNKNOWN
    # Round V D2 (FLIPPED from UNKNOWN): the fully-declared bench DECLARES an inventory, and the retro-DA leaves
    # are structure-keyed, CONSUMED (positive-demand) species absent from every declared bottle -> no G+ edge ->
    # a provable material BLOCK. Still never FIT.
    fitbench = assess(isopentyl_capability_fit_bench(), req, readiness)
    assert fitbench.material.status is CapabilityStatus.BLOCKED
    assert fitbench.overall is CapabilityStatus.BLOCKED


# =============================================================================================================
# 4. D6 -- UNCONSTRAINED with a real demand is UNKNOWN, never a free FIT (kills M29)
# =============================================================================================================

def test_d6_physical_all_none_ceiling_with_a_real_route_demand_is_unknown():
    req = _reqs(physical=PhysicalBounds.of(max_temperature_k=416.15))
    a = assess(_profile(), req, _ps_readiness())  # profile physical_bounds unconstrained (all-None)
    assert a.physical.status is CapabilityStatus.UNKNOWN
    assert a.overall is CapabilityStatus.UNKNOWN


def test_d6_physical_no_demand_and_no_bound_is_unconstrained_and_rides():
    from smartchem.conditions import Interval
    from smartchem.process_constraints import ProcessRequirements
    # X-high D15: the process axis is never UNCONSTRAINED for a real step, so this physical-isolation test carries a
    # fully declared step record + bench (the process axis is then a genuine FIT, not a free ride).
    record = ProcessRequirements(workup_included=True, provenance="fixture: fully declared step",
                                 elapsed_minutes=Interval(0, 60, "min"), active_minutes=Interval(0, 10, "min"),
                                 attention=Attention.PASSIVE, agitation=Agitation.NONE)
    bounds = ProcessBounds.of(max_step_minutes=600.0, max_total_minutes=600.0, max_active_minutes=60.0,
                              allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                              allowed_agitation=tuple(Agitation))
    req = _reqs(physical=PhysicalBounds.unconstrained(), process=(record,))
    # Round V D13: an absent budget is UNDECLARED (UNKNOWN); the explicit operator NO_LIMIT preference is declared
    # here so this test isolates the physical axis's UNCONSTRAINED ride.
    a = assess(_profile(no_limit_dimensions=frozenset({"budget"}), process_bounds=bounds), req, _ps_readiness())
    assert a.physical.status is CapabilityStatus.UNCONSTRAINED
    assert a.overall is CapabilityStatus.FIT  # genuinely outside the question -> rides to FIT


def test_d6_process_all_none_bounds_with_a_real_process_demand_is_unknown():
    from smartchem.process_constraints import ProcessRequirements
    demand = ProcessRequirements(attention=Attention.PERIODIC, provenance="fixture: a real declared demand")
    assert demand.is_declared
    a = assess(_profile(), _reqs(process=(demand,)), _ps_readiness())  # bounds unconstrained
    assert a.process.status is CapabilityStatus.UNKNOWN
    assert a.overall is CapabilityStatus.UNKNOWN


# =============================================================================================================
# 5. D7 -- budget denomination guard (kills M30/M31)
# =============================================================================================================

def test_d7_mismatched_budget_denomination_is_unknown_never_compared_by_raw_number():
    route_cost = CostVector(cash=5.0, currency="USD", unit="metric ton")
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    a = assess(_profile(budget=budget), _reqs(monetary=route_cost), _ps_readiness())
    assert a.monetary.status is CapabilityStatus.UNKNOWN
    assert "denomination" in " ".join(a.monetary.reasons).lower()


def test_d7_matching_denomination_within_budget_still_fits():
    route_cost = CostVector(cash=50.0, currency="USD", unit="USD")
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    a = assess(_profile(budget=budget), _reqs(monetary=route_cost), _ps_readiness())
    assert a.monetary.status is CapabilityStatus.FIT


# =============================================================================================================
# 6. D8 -- ventilation is a surfaced RESERVED axis; OUTDOOR never clears containment (M6)
# =============================================================================================================

def test_d8_ventilation_is_a_surfaced_reserved_not_applicable_axis():
    a = assess(_profile(), _reqs(), _ps_readiness())
    assert a.ventilation.status is CapabilityStatus.NOT_APPLICABLE
    assert "RESERVED" in " ".join(a.ventilation.reasons)


def test_m6_outdoor_ventilation_never_clears_a_containment_requirement():
    from smartchem.capability.enums import VentilationCapability
    req = _reqs(containment=frozenset({ContainmentCapability.FUME_HOOD}))
    profile = _profile(containment=frozenset(), ventilation=frozenset({VentilationCapability.OUTDOOR}))
    a = assess(profile, req, _ps_readiness())
    assert a.containment.status is CapabilityStatus.BLOCKED
    assert a.overall is CapabilityStatus.BLOCKED


# =============================================================================================================
# 7. D9 -- resolved procedure hazard forces containment (non-vacuous); unresolvable is surfaced
# =============================================================================================================

def test_d9_isopentyl_h2so4_forces_containment_and_is_named():
    """The M33 kill, non-vacuous: the H2SO4 catalyst is a procedure-only, structure-resolvable species whose
    sourced GHS record (H314) forces FUME_HOOD -- and the contribution is NAMED in the requirement's
    containment reasons, so a mutant that drops procedure-only hazards is caught by a real discriminator."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    assert req.containment == frozenset({ContainmentCapability.FUME_HOOD})
    joined = " ".join(req.containment_reasons)
    assert "sulfuric acid" in joined and "H314" in joined
    # the unresolvable ionic auxiliaries are SURFACED, never silently skipped, never a fabricated requirement.
    assert any("sodium bicarbonate" in r for r in req.hazard_unresolved)


def test_d9_unresolved_hazards_cap_containment_at_unknown_and_drive_overall_unknown():
    """Round IV F47 INVERSION: the OLD contract said the visible unresolved-hazard note did NOT force
    overall UNKNOWN (containment rode to FIT and the FIT positive survived). It now DOES. The ionic
    NaHCO3/NaCl/MgSO4 auxiliaries carry an unresolved hazard status, so the containment capability they
    require CANNOT be determined -- containment caps at UNKNOWN (the '(F47)' note surfaced in its reasons),
    and that drives overall UNKNOWN. Both contributions are still SURFACED, never silenced: the resolved
    H2SO4 (H314) that forces FUME_HOOD and the unresolved ionic-auxiliary note. (The sibling
    ``test_d9_isopentyl_h2so4_forces_containment_and_is_named`` still pins the REQUIREMENT-level surfacing.)"""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    a = assess(isopentyl_capability_fit_bench(), req, evaluate_route(route))
    reasons = " ".join(a.containment.reasons)
    assert "sulfuric acid" in reasons  # resolved-hazard contribution still surfaced
    assert "sodium bicarbonate" in reasons  # unresolved-hazard note still surfaced
    assert "(F47)" in reasons  # the inversion is named on the axis it now governs
    assert a.containment.status is CapabilityStatus.UNKNOWN
    assert a.overall is CapabilityStatus.UNKNOWN


# =============================================================================================================
# 8. D5 -- measurement compared on the SPECIFIC method (kills M28); VERIFY apparatus skipped from equipment
# =============================================================================================================

def test_d5_measurement_requires_the_specific_method_not_the_coarse_tier():
    """M28: a required INFRARED_SPECTROSCOPY is NOT satisfied by a non-empty available set that lacks IR
    (MASS + MELTING_POINT), even though something is present -- the comparison is member-against-member."""
    req = _reqs(measurement=frozenset({MeasurementMethod.INFRARED_SPECTROSCOPY}))
    profile = _profile(measurement=frozenset({MeasurementMethod.MASS, MeasurementMethod.MELTING_POINT}))
    a = assess(profile, req, _ps_readiness())
    assert a.measurement.status is CapabilityStatus.BLOCKED
    assert "INFRARED_SPECTROSCOPY" in " ".join(a.measurement.reasons)


def test_d5_untabled_verify_apparatus_caps_measurement_at_unknown():
    req = _reqs(measurement=frozenset({MeasurementMethod.MASS}), measurement_unrecognized=("gc-ms",))
    profile = _profile(measurement=frozenset(MeasurementMethod))  # owns every method
    a = assess(profile, req, _ps_readiness())
    assert a.measurement.status is CapabilityStatus.UNKNOWN
    assert "gc-ms" in " ".join(a.measurement.reasons)


def test_d5_verify_apparatus_is_not_counted_as_equipment():
    """The VERIFY ops carry 'analytical balance'/'infrared spectrometer' -- a measurement method, not
    glassware. The equipment axis must NOT carry a phantom BALANCE requirement from them (D5 skip)."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    assert EquipmentCapability.BALANCE not in req.equipment
    assert MeasurementMethod.MASS in req.measurement
    assert MeasurementMethod.INFRARED_SPECTROSCOPY in req.measurement


# =============================================================================================================
# 9. MaterialRequirement honesty: identity-or-name, gateless-absent-is-unknown
# =============================================================================================================

def test_material_requirement_needs_identity_or_name():
    with pytest.raises(ValueError):
        MaterialRequirement(identity=None, phase=None, quantity=QuantityDemand.unstated(),
                            role="reactant", evidence_source="x", name=None)


def test_consumed_species_absent_from_a_declared_inventory_is_a_provable_block():
    """Round V D2 -- FLIPPED from Round IV's "gateless absent is UNKNOWN". Every requirement is a CONSUMED demand
    (quantity is never ``None``: here an UNKNOWN, i.e. real and positive but unsized). A structure-keyed species with
    a positive demand and NO G+ edge in a DECLARED inventory is a provable material negative -> BLOCKED. (An EMPTY
    inventory stays UNKNOWN -- nobody declared a pantry -- and an UNTYPED raw-text requirement with no edge stays
    UNKNOWN, since absence under a raw string proves nothing: both pinned below.)"""
    water = resolve_target("water", InputKind.NAME).canonical()
    requirement = MaterialRequirement(
        identity=water, phase=None, quantity=QuantityDemand.unstated(),
        role="procedure-only auxiliary", evidence_source="x", name="water")
    req = _reqs(material=(requirement,))
    a = assess(_profile(material_inventory=material_library.isopentyl_lab_inventory()), req, _ps_readiness())
    assert a.material.status is CapabilityStatus.BLOCKED
    assert assess(_profile(), req, _ps_readiness()).material.status is CapabilityStatus.UNKNOWN
    untyped = MaterialRequirement(
        identity=None, phase=None, quantity=QuantityDemand.unstated(), role="untyped source material",
        evidence_source="x", name="some raw source phrase",
        specification=MaterialSpecification(unresolved_terms=("untyped source material: some raw source phrase",)),
        untyped_source_text=True)
    b = assess(_profile(material_inventory=material_library.isopentyl_lab_inventory()),
               _reqs(material=(untyped,)), _ps_readiness())
    assert b.material.status is CapabilityStatus.UNKNOWN
