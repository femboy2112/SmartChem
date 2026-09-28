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
from smartchem.capability.presets import isopentyl_capability_fit_bench, poor_man, research_lab
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.data import material_library
from smartchem.data.material_library import household_white_vinegar
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

def _vinegar_for_glacial_inventory():
    """The fully-declared FIT inventory with ONE bottle swapped: glacial acetic acid -> household vinegar.
    Every OTHER reactant and auxiliary is still fully stocked, so the material axis blocks on the acetic-acid
    axis ALONE -- a clean single-axis vinegar discriminator, not a strawman missing half the pantry."""
    full = material_library.isopentyl_fully_declared_inventory()
    kept = tuple(s for s in full if "glacial-acetic" not in s.material_id)
    return kept + (household_white_vinegar(),)


def test_gate_18_fully_declared_custom_collapses_to_unknown_not_capability_fit():
    """Round IV: the fully-declared Custom bench NO LONGER reaches CAPABILITY_FIT -- the honest ceiling, not
    a regression to paper over. The bench still stocks the WHOLE isopentyl procedure, so the MATERIAL axis is
    genuinely FIT (this file's original point -- a well-stocked bench earns its material positive -- still
    holds). But three whole-path semantic axes now collapse to UNKNOWN from the source itself: process (F56,
    the undeclared elapsed CEILING beyond the timed 1-hr reflux floor), containment (F47, the unresolved
    ionic-auxiliary hazards), waste (F49, no sourced disposal routing). Overall UNKNOWN, is_capability_fit
    False. The Round-III FIT rode the process-time-omission=unlimited-patience assumption F56 retires; the
    gate was NOT weakened to preserve the positive -- a vanishing positive is scientific information."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    assessment = assess(isopentyl_capability_fit_bench(), requirements, evaluate_route(route))

    assert assessment.material.status is CapabilityStatus.FIT
    assert assessment.process.status is CapabilityStatus.UNKNOWN
    assert assessment.containment.status is CapabilityStatus.UNKNOWN
    assert assessment.waste.status is CapabilityStatus.UNKNOWN
    assert assessment.overall is CapabilityStatus.UNKNOWN
    assert assessment.is_capability_fit is False


def test_gate_18_two_reactant_bottles_no_longer_fit_now_auxiliaries_participate():
    """The retired floor is DEAD (D1, kills M23) and procedure-only auxiliaries now PARTICIPATE (D2, kills
    M24): a research-lab stocked with ONLY the two reagent bottles (isoamyl alcohol + glacial acetic acid)
    -- the pre-Round-III 'positive' -- is now BLOCKED, because the H2SO4 catalyst, the NaHCO3/NaCl/MgSO4
    washes+drier and the water it does NOT stock are absent from every bottle. FIT is earned only by
    actually possessing the whole procedure, never by a reaction-class label manufacturing a floor."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = research_lab(material_inventory=material_library.isopentyl_lab_inventory())
    assessment = assess(profile, requirements, evaluate_route(route))

    assert assessment.material.status is CapabilityStatus.BLOCKED
    joined = " ".join(assessment.material.reasons)
    assert "magnesium sulfate" in joined  # an auxiliary that is absent -> a provable material negative
    assert assessment.overall is CapabilityStatus.BLOCKED


def test_gate_18_vinegar_control_cannot_masquerade_as_glacial_acetic_acid():
    """M1/M2/M4 shape: the fully-declared FIT bench with ONE bottle swapped -- glacial acetic acid ->
    household vinegar, keyed on the identical acetic-acid structure. Vinegar (few-% aqueous) BLOCKS the
    acetic-acid requirement on BOTH phase (AQUEOUS_SOLUTION != the neat LIQUID glacial formulation) AND assay
    (best case 0.08 << the >=0.99 compendial floor). It must BLOCK, never FIT, or the material axis is not
    discriminating -- and the discrimination is now phase-first per D1/D4, assay reinforcing."""
    route = _isopentyl_route()
    requirements = compile_capability_requirements(route)
    profile = isopentyl_capability_fit_bench(material_inventory=_vinegar_for_glacial_inventory())
    assessment = assess(profile, requirements, evaluate_route(route))

    assert assessment.material.status is CapabilityStatus.BLOCKED
    joined_reasons = " ".join(assessment.material.reasons)
    # Round IV: the acetic-acid reason now names the compendial BAND, not a bare "0.9900" scalar -- the
    # vinegar bottle's composition is provably outside the [0.990, 1.000] floor it can never clear.
    assert "[0.990, 1.000]" in joined_reasons
    assert "phase" in joined_reasons.lower()  # phase is the D1/D4 discriminator too
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
