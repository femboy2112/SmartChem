"""v0.9 Capability Compiler -- gate #18, CAPABILITY_FIT positive real (Wave B).

**Chart note.** Every earlier v0.9 material test proved the fold refuses to fabricate a FIT (empty
inventory -> UNKNOWN, unknown fraction -> UNKNOWN, wrong isomer -> BLOCKED). None of them proved the fold
can reach a genuine positive when a bench is actually well-stocked -- that's this file's one job. A real,
LibreTexts-sourced, searched isopentyl-acetate route, a curated DERIVED_WITH_ERROR stock library
(:mod:`smartchem.data.material_library`), and the reaction-type-keyed 0.98 assay floor
(:mod:`smartchem.capability.requirements`) all have to line up cleanly for ``assess()`` to reach
``CapabilityStatus.FIT``. The vinegar control is the discriminating incision: swap ONE bottle for a
structurally-identical-but-dilute one and the same profile must BLOCK, not FIT -- proof the positive
result is earned by the assay interval, not by the material axis going soft.
"""
from __future__ import annotations

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import assess
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.presets import poor_man, research_lab
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.data import material_library
from smartchem.experiment import routes as rt
from smartchem.experiment.readiness import evaluate_route
from smartchem.identity_parse import InputKind, resolve_target

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)


# -- shared plumbing: the same real, searched, source-backed route as tests/test_v0_9_capability_core.py -------

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


# -- gate #18: CAPABILITY_FIT positive, real error-bounded data ------------------------------------------------

def test_gate_18_capability_fit_positive_with_the_stocked_research_lab():
    """The whole point: a research-lab bench actually stocked with reagent-grade isoamyl alcohol and
    glacial acetic acid (:func:`material_library.isopentyl_lab_inventory`) reaches genuine ``FIT`` on the
    real searched isopentyl-acetate route -- material axis included, not just the equipment/containment
    axes earlier rounds already proved."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = research_lab(material_inventory=material_library.isopentyl_lab_inventory())
    assessment = assess(profile, requirements, evaluate_route(route))

    # material axis: glacial acetic acid worst-case 0.995 >= the derived 0.98 floor; isoamyl alcohol
    # worst-case 0.98 >= 0.98 -- both leaves SATISFY, so the axis is FIT, not merely NOT_APPLICABLE.
    assert assessment.material.status is CapabilityStatus.FIT
    assert assessment.overall is CapabilityStatus.FIT
    assert assessment.is_capability_fit is True


def test_gate_18_vinegar_control_cannot_masquerade_as_glacial_acetic_acid():
    """M1/M2/M4 shape: the SAME profile, the SAME route, the SAME isoamyl alcohol bottle -- only the
    acetic-acid bottle is swapped for household vinegar
    (:func:`material_library.isopentyl_vinegar_inventory`), keyed on the identical acetic-acid structure.
    Vinegar's worst-case 0.08 mass fraction is nowhere near the derived 0.98 floor: this must BLOCK, never
    FIT, or the material axis is not actually discriminating on assay."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = research_lab(material_inventory=material_library.isopentyl_vinegar_inventory())
    assessment = assess(profile, requirements, evaluate_route(route))

    assert assessment.material.status is CapabilityStatus.BLOCKED
    joined_reasons = " ".join(assessment.material.reasons)
    assert "0.9800" in joined_reasons  # the derived floor the vinegar bottle provably cannot clear
    assert assessment.overall is CapabilityStatus.BLOCKED
    assert assessment.is_capability_fit is False


# -- regression: the derivation must not disturb the pre-existing matrix ----------------------------------------

def test_research_lab_with_no_declared_stock_is_still_unknown_not_fit():
    """Unchanged F2 default: a ``research_lab()`` bench with NO declared material inventory stays UNKNOWN
    on the material axis (an empty pantry never vacuously FITs) and therefore UNKNOWN overall -- the
    esterification assay derivation only ever tightens a requirement that IS checked against real stock; it
    does not conjure stock that was never declared."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = research_lab()  # material_inventory=() default
    assessment = assess(profile, requirements, evaluate_route(route))

    assert assessment.material.status is CapabilityStatus.UNKNOWN
    assert assessment.overall is CapabilityStatus.UNKNOWN


def test_poor_man_is_still_blocked_on_equipment_regardless_of_the_material_derivation():
    """Unchanged FREEZE decision 6 shape: ``poor_man()`` has no reflux condenser / distillation rig, so the
    equipment axis BLOCKS the real isopentyl-acetate route exactly as it always did -- BLOCKED still beats
    UNKNOWN/FIT overall, whether or not a material inventory is declared."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = poor_man(material_inventory=material_library.isopentyl_lab_inventory())
    assessment = assess(profile, requirements, evaluate_route(route))

    assert assessment.equipment.status is CapabilityStatus.BLOCKED
    assert assessment.overall is CapabilityStatus.BLOCKED
