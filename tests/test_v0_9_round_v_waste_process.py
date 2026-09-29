"""Round V Wave B -- waste-stream projection (D9) + dimension declaration semantics (D10).

F76: an empty-GHS byproduct is NEVER AQUEOUS_NEUTRAL (phase/pH/co-residents unestablished).
F77: catalyst / reactant residuals enter the waste question.
Lane E latent P0: auxiliaries living only in ``materials=`` strings still yield spent streams.
F78/M82: the legacy ProcessBounds law is untouched; NO_LIMIT is an explicit, validated profile declaration.
X-high D17: F-6 (an untyped material introduced by ANY op never vanishes), F-7 (a CATALYST label a step
net-consumes is a role contradiction, never a resolved catalyst category), Part IV (``envelope.medium`` is prose,
never a stream), the role-totality guard; D22: profile v1alpha3.
"""
from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest

from smartchem.capability import waste as waste_mod
from smartchem.capability.declarations import (
    NO_LIMIT_ELIGIBLE,
    DimensionDeclaration,
    budget_state,
    physical_dimension_state,
    process_dimension_state,
)
from smartchem.capability.enums import WasteCapability
from smartchem.capability.presets import (
    CAPABILITY_PROFILE_PRESETS,
    custom,
    isopentyl_capability_fit_bench,
    poor_man,
    research_lab,
)
from smartchem.capability.profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile
from smartchem.capability.waste import derive_waste
from smartchem.constraints import PhysicalBounds
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import ByproductEntry, Fate, HazardFlag, RouteHandling
from smartchem.experiment.handling import verify_handling as real_verify_handling
from smartchem.procedure_evidence import EvidenceField, OperationKind, OperationRole, ProcedureMaterialUse, ProcedureOperation
from smartchem.procedure_evidence import ProcedureMaterialRole as R
from smartchem.process_constraints import (
    Agitation,
    Attention,
    ProcessBounds,
    evaluate_process_requirements,
)
from smartchem.smiles import parse_smiles


def _isopentyl_route():
    """The same real, LibreTexts-sourced, searched isopentyl-acetate route as the gate #18 file (built locally so
    this file does not import the material library)."""
    from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
    from smartchem.experiment import routes as rt
    from smartchem.identity_parse import InputKind, resolve_target

    target = resolve_target("isopentyl acetate", InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in ("water", "acetic acid"))
    have = (resolve_target("isopentyl alcohol", InputKind.AUTO).canonical(),)
    result = rt.search_routes(target, reagents=reag, available=have, max_depth=3,
                              registry=resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE))
    for route in result.routes:
        if any(step.envelope.procedure is not None for step in route.steps):
            return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


@pytest.fixture(scope="module")
def iso_route():
    return _isopentyl_route()


def _with_step0(route, **envelope_changes):
    step = route.steps[0]
    env = dataclasses.replace(step.envelope, **envelope_changes)
    return dataclasses.replace(route, steps=(dataclasses.replace(step, envelope=env),) + route.steps[1:])


def _strip_uses(route, keep):
    """Lane E P0 counterfactual: keep only ``keep``-role typed uses; every other auxiliary survives ONLY as a
    ``materials=`` string (schema-legal: material_uses is optional)."""
    proc = route.steps[0].envelope.procedure
    ops = tuple(
        dataclasses.replace(op, material_uses=tuple(u for u in op.material_uses if u.role in keep))
        for op in proc.operations
    )
    return _with_step0(route, procedure=dataclasses.replace(proc, operations=ops))


# -- F76: empty GHS never earns AQUEOUS_NEUTRAL -----------------------------------------------------------------

_F76_CASES = [
    ("stearic acid", "CCCCCCCCCCCCCCCCCC(=O)O", Fate.UNKNOWN),
    ("stearic acid", "CCCCCCCCCCCCCCCCCC(=O)O", Fate.CONDENSED),
    ("nitrogen", "N#N", Fate.UNKNOWN),
    ("water", "O", Fate.CONDENSED),
]


def _inject(monkeypatch, name, smiles, fate, ghs=()):
    mol = parse_smiles(smiles)

    def fake(route, **kw):
        h = real_verify_handling(route, **kw)
        s0 = h.steps[0]
        b = ByproductEntry(molecule=mol, moles_per_target=Fraction(1), fate=fate, hazard_name=name,
                           reason="probe: assessed record, phase as labelled")
        flag = HazardFlag(name=name, role="byproduct", ghs_codes=tuple(ghs), summary="probe", provenance="probe")
        s0b = dataclasses.replace(s0, byproducts=s0.byproducts + (b,), hazards=s0.hazards + (flag,))
        return RouteHandling((s0b,) + h.steps[1:])

    monkeypatch.setattr(waste_mod, "verify_handling", fake)


@pytest.mark.parametrize("name,smiles,fate", _F76_CASES)
def test_f76_empty_ghs_byproduct_is_unresolved_never_aqueous_neutral(monkeypatch, iso_route, name, smiles, fate):
    _inject(monkeypatch, name, smiles, fate)
    cats, _reasons, unresolved = derive_waste(iso_route)
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    hits = [u for u in unresolved if f"({name}, empty GHS)" in u and "untyped waste stream" in u]
    assert hits, unresolved
    assert any(f"fate={fate.value}" in h for h in hits)  # the reason quotes the injected (real) Fate


def test_f76_real_isopentyl_water_byproduct_quotes_real_fate(iso_route):
    cats, reasons, unresolved = derive_waste(iso_route)
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    assert not any("ASSESSED-benign condensed" in r for r in reasons)
    water = [u for u in unresolved if u.startswith("waste: byproduct H2O")]
    assert water and "fate=UNKNOWN" in water[0]


def test_empty_ghs_offgas_captures_and_stays_unresolved(monkeypatch, iso_route):
    _inject(monkeypatch, "nitrogen", "N#N", Fate.OFFGAS)
    cats, _r, unresolved = derive_waste(iso_route)
    assert WasteCapability.OFFGAS_CAPTURE in cats
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    assert any("(nitrogen, empty GHS)" in u for u in unresolved)


def test_real_ghs_unknown_fate_is_hazardous_and_unresolved(monkeypatch, iso_route):
    _inject(monkeypatch, "probe toxin", "CCCl", Fate.UNKNOWN, ghs=("H301",))
    cats, reasons, unresolved = derive_waste(iso_route)
    assert WasteCapability.HAZARDOUS in cats
    assert any("H301" in r and "fate=UNKNOWN" in r for r in reasons)
    assert any("probe toxin" in u and "phase is UNASSESSED" in u for u in unresolved)


def test_hazard_name_without_ledger_flag_is_unresolved_not_benign(monkeypatch, iso_route):
    mol = parse_smiles("CCO")

    def fake(route, **kw):
        h = real_verify_handling(route, **kw)
        s0 = h.steps[0]
        b = ByproductEntry(molecule=mol, moles_per_target=Fraction(1), fate=Fate.CONDENSED,
                           hazard_name="ghost record", reason="probe")
        return RouteHandling((dataclasses.replace(s0, byproducts=s0.byproducts + (b,)),) + h.steps[1:])

    monkeypatch.setattr(waste_mod, "verify_handling", fake)
    cats, _r, unresolved = derive_waste(iso_route)
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    assert any("ghost record" in u for u in unresolved)


# -- F77: residuals ---------------------------------------------------------------------------------------------

def test_isopentyl_residuals(iso_route):
    cats, reasons, unresolved = derive_waste(iso_route)
    assert any("'acetic acid' (REACTANT) residual" in u for u in unresolved)
    assert any("'isopentyl alcohol' (SUBSTRATE) residual" in u for u in unresolved)
    assert WasteCapability.HAZARDOUS in cats
    assert any("catalyst residual 'sulfuric acid'" in r and "H314" in r for r in reasons)


def test_catalyst_use_alone_is_a_residual(iso_route):
    # drop the envelope catalyst declaration: the typed CATALYST use still yields the HAZARDOUS residual
    route = _with_step0(iso_route, catalysts=())
    cats, reasons, _u = derive_waste(route)
    assert WasteCapability.HAZARDOUS in cats
    assert any("catalyst residual 'sulfuric acid'" in r and "CATALYST use" in r for r in reasons)


def test_envelope_catalyst_alone_is_a_residual(iso_route):
    route = _strip_uses(iso_route, keep={R.SUBSTRATE, R.REACTANT})
    cats, reasons, _u = derive_waste(route)
    assert WasteCapability.HAZARDOUS in cats
    assert any("catalyst residual 'sulfuric acid'" in r and "envelope catalyst" in r for r in reasons)


def test_unknown_catalyst_is_unresolved_not_dropped(iso_route):
    route = _with_step0(_strip_uses(iso_route, keep={R.SUBSTRATE, R.REACTANT}), catalysts=("unobtainium salt",))
    cats, _r, unresolved = derive_waste(route)
    assert any("catalyst residual 'unobtainium salt'" in u for u in unresolved)


def test_step_without_procedure_every_input_is_a_residual(iso_route):
    route = _with_step0(iso_route, procedure=None)
    _c, _r, unresolved = derive_waste(route)
    inputs = [u for u in unresolved if "has no typed procedure use" in u]
    assert len(inputs) == len(set(iso_route.steps[0].reactants) | set(iso_route.steps[0].reagents))
    assert len(inputs) >= 2


_ISOPENTYL_MEDIUM_SENTENCE = "neat; acid-catalyzed (conc. H2SO4); reflux then fractional distillation"


@pytest.mark.parametrize("medium", ["sulfuric acid", "unobtainium broth", _ISOPENTYL_MEDIUM_SENTENCE])
def test_part_iv_medium_is_provenance_never_a_stream(iso_route, medium):
    """Part IV: ``envelope.medium`` is a condition DESCRIPTION. Before D17 the whole sentence became a 'reaction
    medium' spent stream (and a HAZARDOUS category when the words happened to name a hazard record). It is now
    provenance only: the waste projection is invariant under the medium text."""
    baseline = derive_waste(_with_step0(iso_route, medium=""))
    with_medium = derive_waste(_with_step0(iso_route, medium=medium))
    assert with_medium == baseline
    assert not any("reaction medium" in line for part in with_medium[1:] for line in part)


# -- Lane E latent P0: spent streams from OPERATIONS -------------------------------------------------------------

def test_p0_counterfactual_materials_strings_still_yield_spent_streams(iso_route):
    route = _strip_uses(iso_route, keep={R.SUBSTRATE, R.REACTANT, R.CATALYST})
    cats, _r, unresolved = derive_waste(route)
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    streams = [u for u in unresolved if "leaves a spent stream" in u]
    # SEPARATE(4), WASH(5,6,7), DRY(8), DISTILL(9)
    for ordinal in (4, 5, 6, 7, 8, 9):
        assert any(f"op #{ordinal} " in s for s in streams), (ordinal, streams)
    # Wave-C K4: op.materials are aligned to the typed names (the raw phrase lives in the use's formulation text)
    assert any("sodium bicarbonate" in s for s in streams)
    assert any("magnesium sulfate" in s for s in streams)
    assert unresolved  # the waste axis can never be FIT on this record


def test_p0_counterfactual_no_uses_at_all(iso_route):
    route = _strip_uses(iso_route, keep=set())
    _c, _r, unresolved = derive_waste(route)
    assert any("op #9 DISTILL" in u and "no named materials" in u for u in unresolved)
    # untyped reactants still become residuals via the step-input rule
    assert any("has no typed procedure use" in u for u in unresolved)


def test_derive_waste_is_pure_sorted_unique(iso_route):
    a = derive_waste(iso_route)
    b = derive_waste(iso_route)
    assert a == b
    for part in a[1:]:
        assert list(part) == sorted(set(part))
    assert WasteCapability.AQUEOUS_NEUTRAL not in a[0]
    with pytest.raises(TypeError):
        derive_waste("not a route")


# -- X-high D17 F-6: nothing a procedure introduces may vanish ---------------------------------------------------

def _append_op(route, kind, role, materials=(), uses=()):
    """Append one op to step 0's real procedure (ordinals stay contiguous; a QUENCH op gets a PRESENT quench field so
    the procedure stays coherent -- schema-legal source evidence, the attacker's own material)."""
    proc = route.steps[0].envelope.procedure
    op = ProcedureOperation(ordinal=len(proc.operations) + 1, kind=kind, role=role, materials=tuple(materials),
                            material_uses=tuple(uses), locator="probe")
    changes = {"operations": proc.operations + (op,)}
    if role is OperationRole.QUENCH and not proc.quench.is_present:
        changes["quench"] = EvidenceField.present("probe quench", "probe")
    return _with_step0(route, procedure=dataclasses.replace(proc, **changes)), op.ordinal


def _f6(unresolved, name):
    return [u for u in unresolved if "introduces untyped material" in u and f"{name!r}" in u]


@pytest.mark.parametrize("kind,role,material", [
    (OperationKind.ADD, OperationRole.QUENCH, "ice water"),
    (OperationKind.ADD, OperationRole.REACTION, "triethylamine"),
    (OperationKind.ADD, OperationRole.OTHER, "acetone"),
    (OperationKind.MIX, OperationRole.OTHER, "toluene"),
    (OperationKind.HEAT, OperationRole.OTHER, "ethanol"),
    (OperationKind.HOLD, OperationRole.OTHER, "dichloromethane"),
    (OperationKind.COOL, OperationRole.OTHER, "ice"),
])
def test_f6_untyped_material_on_any_op_kind_is_an_unresolved_obligation(iso_route, kind, role, material):
    """F-6: before D17 only spent-stream ops (WASH/RECRYSTALLIZATION, SEPARATE/FILTER/DRY/DISTILL) and typed uses made
    an obligation, so an untyped material charged by an ADD/QUENCH/MIX/HEAT/HOLD/COOL op had NO waste obligation at
    all (0 lines naming it). Now each such introduction is its own unresolved obligation, quoting its op."""
    assert not _f6(derive_waste(iso_route)[2], material)
    route, ordinal = _append_op(iso_route, kind, role, materials=(material,))
    hits = _f6(derive_waste(route)[2], material)
    assert len(hits) == 1, hits
    assert f"op #{ordinal} {kind.value}/{role.value}" in hits[0] and "disposal routing is UNKNOWN" in hits[0]


def test_f6_fires_on_a_spent_stream_op_beside_its_typed_uses(iso_route):
    """A SEPARATE op's stream line names ONLY its typed uses when it has any -- an extra untyped string on the same op
    would go unnamed. F-6 gives it its own line."""
    brine = ProcedureMaterialUse(name="brine", role=R.WASH, evidence_source="probe")
    route, ordinal = _append_op(iso_route, OperationKind.SEPARATE, OperationRole.OTHER,
                                materials=("brine", "hexane"), uses=(brine,))
    unresolved = derive_waste(route)[2]
    stream = [u for u in unresolved if f"op #{ordinal} SEPARATE/OTHER leaves a spent stream" in u]
    assert stream and "hexane" not in stream[0]
    assert len(_f6(unresolved, "hexane")) == 1
    assert not _f6(unresolved, "brine")  # the typed use covers its own exact name


def test_f6_an_introduction_masked_by_a_same_named_stream_elsewhere_still_surfaces(iso_route):
    """The paracetamol shape: op A charges untyped 'water'; a LATER op carries a typed RINSE use named 'water'. The
    name-deduplicated spent-stream line used to be the only 'water' obligation, silently absorbing op A's
    introduction. Coverage is per OP, so op A's untyped introduction keeps its own line; op B's typed use does not."""
    route, a = _append_op(iso_route, OperationKind.ADD, OperationRole.OTHER, materials=("water",))
    rinse = ProcedureMaterialUse(name="water", role=R.RINSE, evidence_source="probe")
    route, b = _append_op(route, OperationKind.FILTER, OperationRole.OTHER, materials=("water",), uses=(rinse,))
    hits = _f6(derive_waste(route)[2], "water")
    assert len(hits) == 1 and f"op #{a} ADD/OTHER" in hits[0], hits


def test_f6_coverage_is_exact_fold_equality_never_a_substring(iso_route):
    use = ProcedureMaterialUse(name="brine", role=R.WASH, evidence_source="probe")
    route, _ = _append_op(iso_route, OperationKind.ADD, OperationRole.OTHER,
                          materials=("  Brine ", "brine and toluene"), uses=(use,))
    unresolved = derive_waste(route)[2]
    assert not _f6(unresolved, "Brine")                    # case/whitespace fold -> covered
    assert len(_f6(unresolved, "brine and toluene")) == 1  # a second species hidden in a phrase stays uncovered


def test_f6_real_isopentyl_record_introduces_nothing_untyped(iso_route):
    # every isopentyl op.materials string is aligned to a typed use of its own op (Wave-C K4) -> no F-6 line
    assert not [u for u in derive_waste(iso_route)[2] if "introduces untyped material" in u]


def test_role_totality_guard_refuses_a_role_with_no_waste_obligation(monkeypatch):
    waste_mod._check_role_totality()  # the shipped map is total
    monkeypatch.setattr(waste_mod, "_SPENT_STREAM_ROLES", waste_mod._SPENT_STREAM_ROLES - {R.RINSE})
    with pytest.raises(RuntimeError, match="RINSE"):
        waste_mod._check_role_totality()


# -- X-high D17 F-7: a CATALYST label must agree with the balanced reaction ------------------------------------------

def _relabel(route, name, role):
    proc = route.steps[0].envelope.procedure
    ops = tuple(dataclasses.replace(op, material_uses=tuple(
        dataclasses.replace(u, role=role) if u.name == name else u for u in op.material_uses)) for op in proc.operations)
    return _with_step0(route, procedure=dataclasses.replace(proc, operations=ops))


def test_f7_net_consumed_reactant_relabelled_catalyst_earns_no_resolved_category(iso_route):
    """F-7: relabelling the net-consumed acetic acid REACTANT as a CATALYST used to REPLACE its unresolved residual
    with a resolved 'catalyst residual ... HAZARDOUS' line. Now it is an unresolved role contradiction."""
    step = iso_route.steps[0]
    acetic = next(u for op in step.envelope.procedure.operations for u in op.material_uses if u.name == "acetic acid")
    assert acetic.identity is not None and step.net_consumes(acetic.identity)
    route = _relabel(iso_route, "acetic acid", R.CATALYST)
    cats, reasons, unresolved = derive_waste(route)
    assert not any("'acetic acid'" in r for r in reasons), reasons
    contradiction = [u for u in unresolved if "'acetic acid'" in u and "NET-CONSUMED" in u and "(F-7)" in u]
    assert contradiction, unresolved
    # the genuine catalyst (sulfuric acid: not net-consumed) still earns its resolved HAZARDOUS residual
    assert WasteCapability.HAZARDOUS in cats and any("catalyst residual 'sulfuric acid'" in r for r in reasons)


def test_f7_a_same_named_envelope_catalyst_cannot_smuggle_the_category_back(iso_route):
    """Envelope catalysts are read FIRST and deduplicated by name -- without the pre-pass, declaring
    ``catalysts=('acetic acid',)`` beside the contradicted use would earn the resolved HAZARDOUS line by name."""
    route = _relabel(iso_route, "acetic acid", R.CATALYST)
    route = _with_step0(route, catalysts=("acetic acid",) + tuple(route.steps[0].envelope.catalysts))
    _cats, reasons, unresolved = derive_waste(route)
    assert not any("'acetic acid'" in r for r in reasons), reasons
    assert any("'acetic acid' (step 1 envelope catalyst) is NET-CONSUMED" in u for u in unresolved)


def test_f7_control_no_contradiction_on_the_real_record(iso_route):
    assert not any("NET-CONSUMED" in u for u in derive_waste(iso_route)[2])


# -- D10: declarations + NO_LIMIT validation ---------------------------------------------------------------------

def test_no_limit_eligible_set():
    assert NO_LIMIT_ELIGIBLE == frozenset({"max_step_minutes", "max_total_minutes", "max_active_minutes", "budget"})


@pytest.mark.parametrize("bad", [
    "allowed_attention", "allowed_agitation", "min_check_interval_minutes", "available_equipment",
    "max_temperature_k", "max_pressure_atm", "min_pressure_atm", "min_temperature_k", "bogus",
])
def test_ineligible_no_limit_refused(bad):
    with pytest.raises(ValueError, match="not NO_LIMIT-eligible"):
        custom(profile_id="x", no_limit_dimensions=frozenset({bad}))


def test_bound_and_no_limit_is_contradictory():
    with pytest.raises(ValueError, match="contradictory"):
        custom(profile_id="x", process_bounds=ProcessBounds.of(max_step_minutes=60.0),
               no_limit_dimensions=frozenset({"max_step_minutes"}))
    with pytest.raises(ValueError, match="contradictory"):
        custom(profile_id="x", budget=CostVector(cash=10.0, currency="USD", unit="USD"),
               no_limit_dimensions=frozenset({"budget"}))


def test_no_limit_type_checked():
    with pytest.raises(TypeError):
        custom(profile_id="x", no_limit_dimensions=frozenset({1}))
    base = custom(profile_id="x")
    with pytest.raises(TypeError):
        dataclasses.replace(base, no_limit_dimensions={"max_step_minutes"})


def test_dimension_states():
    p = custom(profile_id="x", process_bounds=ProcessBounds.of(max_total_minutes=120.0),
               physical_bounds=PhysicalBounds.of(max_temperature_k=400.0),
               no_limit_dimensions=frozenset({"max_step_minutes", "budget"}))
    assert process_dimension_state(p, "max_step_minutes") is DimensionDeclaration.NO_LIMIT
    assert process_dimension_state(p, "max_total_minutes") is DimensionDeclaration.DECLARED_BOUND
    assert process_dimension_state(p, "max_active_minutes") is DimensionDeclaration.UNDECLARED
    assert process_dimension_state(p, "allowed_attention") is DimensionDeclaration.UNDECLARED
    assert physical_dimension_state(p, "max_temperature_k") is DimensionDeclaration.DECLARED_BOUND
    assert physical_dimension_state(p, "max_pressure_atm") is DimensionDeclaration.UNDECLARED
    assert physical_dimension_state(p, "min_temperature_k") is DimensionDeclaration.UNDECLARED  # D14 floor dimension
    assert physical_dimension_state(research_lab(), "min_temperature_k") is DimensionDeclaration.DECLARED_BOUND
    assert budget_state(p) is DimensionDeclaration.NO_LIMIT
    assert budget_state(custom(profile_id="y")) is DimensionDeclaration.UNDECLARED
    assert budget_state(poor_man()) is DimensionDeclaration.DECLARED_BOUND
    with pytest.raises(ValueError):
        process_dimension_state(p, "max_temperature_k")
    with pytest.raises(ValueError):
        physical_dimension_state(p, "max_step_minutes")


def test_presets_never_emit_no_limit():
    profiles = [research_lab(), poor_man(), isopentyl_capability_fit_bench()]
    profiles += [builder() for builder in CAPABILITY_PROFILE_PRESETS.values()]
    for p in profiles:
        assert p.no_limit_dimensions == frozenset()
        for dim in ("max_step_minutes", "max_total_minutes"):
            assert process_dimension_state(p, dim) is DimensionDeclaration.DECLARED_BOUND
        assert process_dimension_state(p, "max_active_minutes") is DimensionDeclaration.UNDECLARED
    assert research_lab().process_bounds.max_step_minutes == 10080.0
    assert research_lab().process_bounds.max_total_minutes == 20160.0


def test_profile_schema_bumped_and_digest_covers_no_limit():
    # D22: v1alpha3 (embeds PhysicalBounds v1alpha2 + StockMaterial v1alpha3); the WIP-only v1alpha2 is refused
    assert CAPABILITY_PROFILE_SCHEMA == "smartchem.capability/capability-profile-v1alpha3"
    a = custom(profile_id="x")
    b = custom(profile_id="x", no_limit_dimensions=frozenset({"max_total_minutes"}))
    assert a.profile_digest != b.profile_digest
    for stale in ("smartchem.capability/capability-profile-v1alpha1", "smartchem.capability/capability-profile-v1alpha2"):
        with pytest.raises(ValueError):
            dataclasses.replace(a, schema_version=stale)


def test_profile_codec_round_trips_no_limit():
    from smartchem.service import _capability_profile_from_payload, _capability_profile_to_payload
    p = custom(profile_id="x", no_limit_dimensions=frozenset({"max_step_minutes", "budget"}))
    q = _capability_profile_from_payload(_capability_profile_to_payload(p))
    assert type(q) is CapabilityProfile and q == p and q.profile_digest == p.profile_digest


# -- M82: the legacy ProcessBounds law is untouched ---------------------------------------------------------------

_M82_BOUNDS = [
    ProcessBounds.unconstrained(),
    ProcessBounds.of(allowed_attention=tuple(Attention), allowed_agitation=tuple(Agitation)),
    ProcessBounds.of(max_step_minutes=600, max_total_minutes=1200),
    ProcessBounds.quick(),
    ProcessBounds.low_touch(),
    ProcessBounds.of(max_step_minutes=10080.0, max_total_minutes=20160.0,
                     allowed_attention=tuple(Attention), allowed_agitation=tuple(Agitation)),
]


@pytest.mark.parametrize("bounds", _M82_BOUNDS)
def test_m82_legacy_process_law_identical_inside_or_outside_a_profile(iso_route, bounds):
    reqs = tuple(step.envelope.process for step in iso_route.steps)
    direct = evaluate_process_requirements(reqs, bounds)
    embedded = custom(profile_id="m82", process_bounds=bounds).process_bounds
    assert embedded == bounds
    assert evaluate_process_requirements(reqs, embedded) == direct
    free = [d for d in ("max_step_minutes", "max_total_minutes", "max_active_minutes")
            if getattr(bounds, d) is None]
    if free:
        with_no_limit = custom(profile_id="m82", process_bounds=bounds,
                               no_limit_dimensions=frozenset(free)).process_bounds
        assert evaluate_process_requirements(reqs, with_no_limit) == direct


def test_m82_legacy_none_still_unconstrained(iso_route):
    reqs = tuple(step.envelope.process for step in iso_route.steps)
    fit = evaluate_process_requirements(
        reqs, ProcessBounds.of(allowed_attention=tuple(Attention), allowed_agitation=tuple(Agitation)))
    assert fit.status.value == "FITS"


def test_fit_bench_declares_hazardous_waste_routing_poor_man_does_not():
    # D9: the H2SO4 catalyst residual is a certain HAZARDOUS stream; the hood bench declares routing for it,
    # the kitchen bench does not (-> its waste axis BLOCKS on the isopentyl route, honestly).
    assert WasteCapability.HAZARDOUS in isopentyl_capability_fit_bench().waste_handling
    assert WasteCapability.HAZARDOUS not in poor_man().waste_handling
