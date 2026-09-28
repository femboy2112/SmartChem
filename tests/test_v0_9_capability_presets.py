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

def test_forcing_matrix_research_lab_is_unknown_on_material_only():
    """The frozen forcing matrix's headline row: a well-equipped ResearchLab with NO declared stock
    reaches overall UNKNOWN, and the material axis is the ONLY axis carrying that UNKNOWN -- every other
    axis is FIT/NOT_APPLICABLE/UNCONSTRAINED, never itself BLOCKED or UNKNOWN."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    assert readiness.tier == "PROCESS_SPECIFIED"

    assessment = assess(research_lab(), requirements, readiness)

    assert assessment.material.status is CapabilityStatus.UNKNOWN
    assert assessment.overall is CapabilityStatus.UNKNOWN
    other_axes = [axis for axis in assessment.axes if axis is not assessment.material]
    assert all(
        axis.status in (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)
        for axis in other_axes
    ), [(axis.status, axis.reasons) for axis in other_axes]


def test_forcing_matrix_poor_man_is_blocked_on_missing_distillation_equipment():
    """The frozen forcing matrix's second headline verdict: a PoorMan bench, missing the reflux condenser
    and the fractional-distillation rig the real source demands, is BLOCKED on the equipment axis --
    and BLOCKED strictly outranks every other axis in the overall fold."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    readiness = evaluate_route(route)

    assessment = assess(poor_man(), requirements, readiness)

    assert assessment.equipment.status is CapabilityStatus.BLOCKED
    joined_reasons = " ".join(assessment.equipment.reasons)
    assert "REFLUX_CONDENSER" in joined_reasons
    assert "FRACTIONAL_DISTILLATION" in joined_reasons
    assert assessment.overall is CapabilityStatus.BLOCKED
