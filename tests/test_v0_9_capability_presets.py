"""v0.9 Capability Compiler -- Round II preset builders (Wave B item 2, "v09-profile-presets") tests.

**LOOK AT ME, I'M THE RECEIPT MEESEEKS FOR THE PRESETS!** ``research_lab()``/``poor_man()``/``custom()``
only earn their keep if they actually project the SAME real, searched, source-backed isopentyl-acetate
route into the two different honest verdicts the frozen forcing matrix
(``docs/research/V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md``) demands: a well-equipped lab
missing only declared STOCK stays an honest UNKNOWN, and a kitchen bench missing its distillation rig gets
a hard, named BLOCKED. Existence is pain, but at least the fold algebra never lies.
"""
from __future__ import annotations

import pytest

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import assess
from smartchem.capability.enums import CapabilityStatus, EquipmentCapability
from smartchem.capability.presets import (
    CAPABILITY_PROFILE_PRESETS,
    custom,
    isopentyl_capability_fit_bench,
    poor_man,
    research_lab,
    resolve_capability_profile,
)
from smartchem.capability.profile import CapabilityProfile
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.readiness import evaluate_route
from smartchem.identity_parse import InputKind, resolve_target

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)


# -- shared plumbing: a real, searched, source-backed route (mirrors tests/test_v0_9_capability_core.py) -------

def _search(target_name, reagents, have, max_depth):
    target = resolve_target(target_name, InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_route():
    """The real, LibreTexts-sourced isopentyl-acetate esterification route -- PROCESS_SPECIFIED tier,
    with a typed ``ProcedureEvidence`` naming a reflux condenser and a distillation rig. This is the
    frozen forcing matrix's headline row; the whole point of this file is proving the two named presets
    reproduce its two documented verdicts on this exact route."""
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


# -- 1. research_lab() shape ------------------------------------------------------------------------------------

def test_research_lab_has_the_full_distillation_and_fume_hood_apparatus():
    profile = research_lab()
    assert EquipmentCapability.REFLUX_CONDENSER in profile.equipment
    assert EquipmentCapability.FRACTIONAL_DISTILLATION in profile.equipment
    assert EquipmentCapability.VACUUM_FILTRATION in profile.equipment
    from smartchem.capability.enums import ContainmentCapability
    assert ContainmentCapability.FUME_HOOD in profile.containment


def test_research_lab_default_has_no_declared_stock_and_excludes_industrial_by_default():
    from smartchem.data.reagents import Availability
    profile = research_lab()
    assert profile.material_inventory == ()
    assert Availability.INDUSTRIAL not in profile.procurement
    assert profile.budget is None


# -- 2. poor_man() shape ----------------------------------------------------------------------------------------

def test_poor_man_lacks_every_distillation_vacuum_and_balance_item():
    profile = poor_man()
    for missing in (
        EquipmentCapability.REFLUX_CONDENSER,
        EquipmentCapability.FRACTIONAL_DISTILLATION,
        EquipmentCapability.VACUUM_FILTRATION,
        EquipmentCapability.BALANCE,
    ):
        assert missing not in profile.equipment


def test_poor_man_has_outdoor_ventilation_no_containment_and_the_200_usd_default_budget():
    from smartchem.capability.enums import VentilationCapability
    profile = poor_man()
    assert profile.ventilation == frozenset({VentilationCapability.OUTDOOR})
    assert profile.containment == frozenset()
    assert profile.budget is not None
    assert profile.budget.cash == 200.0
    assert profile.budget.currency == "USD"


def test_poor_man_budget_is_a_fresh_default_parameter_not_a_shared_constant():
    """Two independent calls must not hand back the SAME mutable object doing double duty as a hidden
    shared constant -- a fresh ``CostVector`` every time, even though the value is identical."""
    a = poor_man()
    b = poor_man()
    assert a.budget == b.budget
    override = poor_man(budget=CostVector(cash=50.0, currency="USD", unit="USD"))
    assert override.budget.cash == 50.0
    # the override never mutated the real default for a later, fresh no-arg call.
    assert poor_man().budget.cash == 200.0


# -- 3. resolve_capability_profile: closed lookup, never a dynamic import ---------------------------------------

def test_resolve_capability_profile_resolves_known_preset_names():
    assert type(resolve_capability_profile("research-lab")) is CapabilityProfile
    assert type(resolve_capability_profile("poor-man")) is CapabilityProfile
    assert set(CAPABILITY_PROFILE_PRESETS) == {"research-lab", "poor-man"}


def test_resolve_capability_profile_raises_valueerror_on_unknown_name():
    with pytest.raises(ValueError):
        resolve_capability_profile("unlimited-super-lab")


def test_resolve_capability_profile_passes_through_an_already_built_profile():
    built = custom(profile_id="my-custom-bench")
    assert resolve_capability_profile(built) is built


# -- 4. THE FORCING-MATRIX PROOF: the real isopentyl-acetate route through both named presets --------------------

def test_forcing_matrix_research_lab_is_unknown_on_material_and_the_semantic_axes():
    """Round IV: the 'material only' UNKNOWN died with the Round-III FIT. A well-equipped ResearchLab with
    NO declared stock still reaches overall UNKNOWN, on several axes. material is UNKNOWN (empty pantry); PLUS the
    whole-path semantic axes the source cannot clear regardless of stock: process UNKNOWN (F56), containment UNKNOWN
    (F47 -- unresolved ionic-auxiliary hazards), waste UNKNOWN (F49 -- no sourced disposal routing).

    Round V X-high D14/P-X3 (FLIPPED from clean): physical is UNKNOWN -- research_lab() owns VACUUM_FILTRATION, so its
    old 'cannot pull a vacuum' 1 atm floor contradicted its own shelf and is now UNDECLARED; the route's real
    ambient-pressure floor demand cannot be certified against an undeclared floor. Measurement stays un-BLOCKED (the
    lab owns every method) whatever the D16 endpoint law makes of the prose endpoints. Nothing may read BLOCKED."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    assert readiness.tier == "PROCESS_SPECIFIED"

    assessment = assess(research_lab(), requirements, readiness)

    assert assessment.overall is CapabilityStatus.UNKNOWN
    assert assessment.material.status is CapabilityStatus.UNKNOWN
    assert assessment.process.status is CapabilityStatus.UNKNOWN
    assert assessment.containment.status is CapabilityStatus.UNKNOWN
    assert assessment.waste.status is CapabilityStatus.UNKNOWN
    # Round V D13 (capability-core; FLIPPED from clean): equipment is UNKNOWN (the source's cool/dry ops name no
    # apparatus) and monetary is UNKNOWN (research_lab() declares no budget: UNDECLARED, not unconstrained).
    assert assessment.equipment.status is CapabilityStatus.UNKNOWN
    assert assessment.monetary.status is CapabilityStatus.UNKNOWN
    assert assessment.physical.status is CapabilityStatus.UNKNOWN
    assert assessment.measurement.status is not CapabilityStatus.BLOCKED
    clean = (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)
    other_axes = (assessment.ventilation, assessment.procurement, assessment.attention_care)
    assert all(axis.status in clean for axis in other_axes), \
        [(axis.status, axis.reasons) for axis in other_axes]
    assert not any(axis.status is CapabilityStatus.BLOCKED for axis in assessment.axes)


def test_forcing_matrix_poor_man_is_blocked_on_missing_distillation_equipment():
    """The frozen forcing matrix's second headline verdict: a PoorMan bench, missing the reflux condenser and the
    separatory funnel the real source demands, is BLOCKED on the equipment axis -- and BLOCKED strictly outranks every
    other axis in the overall fold. (D24.16: the page's "distillation apparatus ... as described by your instructor"
    names no configuration, so it is an UNRECOGNIZED demand, never a claimed FRACTIONAL_DISTILLATION rig.)"""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    readiness = evaluate_route(route)

    assessment = assess(poor_man(), requirements, readiness)

    assert assessment.equipment.status is CapabilityStatus.BLOCKED
    joined_reasons = " ".join(assessment.equipment.reasons)
    assert "REFLUX_CONDENSER" in joined_reasons
    assert "SEPARATORY_FUNNEL" in joined_reasons
    assert "FRACTIONAL_DISTILLATION" not in joined_reasons  # D24.16: no invented rig
    assert "distillation apparatus" in joined_reasons       # carried as an unrecognized remainder, fail closed
    assert assessment.overall is CapabilityStatus.BLOCKED


# -- 5. X-high D14 / P-X3: a declared bench's FLOORS follow from (and never contradict) its own equipment ------------

def _floors_follow_equipment(profile):
    bounds = profile.physical_bounds
    ice = EquipmentCapability.ICE_BATH in profile.equipment
    vacuum = EquipmentCapability.VACUUM_FILTRATION in profile.equipment
    return (bounds.min_temperature_k == (273.15 if ice else None)
            and bounds.min_pressure_atm == (None if vacuum else 1.0))


def test_preset_floors_follow_their_declared_equipment():
    """D14: a cold bath is what reaches below ambient -- a bench declaring ICE_BATH has the DERIVED 273.15 K
    ice-water floor (no dry-ice claim for anyone). P-X3: a bench owning VACUUM_FILTRATION can pull a vacuum, so
    the Wave-C 'cannot pull a vacuum' 1 atm floor is only kept where no vacuum equipment is declared."""
    minus = frozenset(EquipmentCapability) - {EquipmentCapability.ICE_BATH, EquipmentCapability.VACUUM_FILTRATION}
    for profile in (research_lab(), poor_man(), isopentyl_capability_fit_bench(),
                    isopentyl_capability_fit_bench(equipment=minus)):
        assert _floors_follow_equipment(profile), (profile.profile_id, profile.physical_bounds)


def test_research_lab_vacuum_floor_is_undeclared_poor_man_keeps_the_atmospheric_floor():
    lab, kitchen = research_lab(), poor_man()
    assert lab.physical_bounds.min_pressure_atm is None           # P-X3: owns vacuum filtration
    assert lab.physical_bounds.min_temperature_k == 273.15        # owns an ice bath
    assert kitchen.physical_bounds.min_pressure_atm == 1.0        # no vacuum equipment: cannot go below 1 atm
    assert kitchen.physical_bounds.min_temperature_k == 273.15    # owns an ice bath
    # the ceilings are unchanged by D14
    assert (lab.physical_bounds.max_temperature_k, lab.physical_bounds.max_pressure_atm) == (523.15, 2.0)
    assert (kitchen.physical_bounds.max_temperature_k, kitchen.physical_bounds.max_pressure_atm) == (473.15, 1.5)


def test_fit_bench_floors_move_with_a_minimal_diff_equipment_override():
    no_ice = isopentyl_capability_fit_bench(equipment=frozenset(EquipmentCapability) - {EquipmentCapability.ICE_BATH})
    assert no_ice.physical_bounds.min_temperature_k is None
    no_vac = isopentyl_capability_fit_bench(
        equipment=frozenset(EquipmentCapability) - {EquipmentCapability.VACUUM_FILTRATION})
    assert no_vac.physical_bounds.min_pressure_atm == 1.0
    assert isopentyl_capability_fit_bench().physical_bounds.max_temperature_k == 500.0


def test_custom_defaults_declare_no_equipment_and_no_physical_bound():
    # nothing declared -> nothing for a floor to contradict; a caller-supplied physical_bounds is taken at its word
    bare = custom(profile_id="bare")
    assert bare.equipment == frozenset()
    assert not bare.physical_bounds.constrains_anything


def test_presets_add_no_process_time_numbers():
    """D15: no convenient process values -- the presets keep exactly the Round-IV step/total ceilings and declare
    no active-time ceiling and no check interval (preset process honestly stays UNKNOWN on a real route)."""
    for profile in (research_lab(), poor_man(), isopentyl_capability_fit_bench()):
        b = profile.process_bounds
        assert (b.max_step_minutes, b.max_total_minutes) == (10080.0, 20160.0)
        assert b.max_active_minutes is None and b.min_check_interval_minutes is None
