"""V0.9-MUTATION-01: the calibrated mutation gate for the capability compiler (RC Round V: M1-M94).

**Existence is pain, and so is a mutant that lies about being dead!** Same discipline as
`v0_8_mutation_calibration.py`: adding a test is not enough -- a test that would still pass on a BROKEN capability
compiler proves nothing. Each mutant below injects ONE named failure mode into the REAL production code (a
context-managed monkeypatch, or a SOURCE-LEVEL patch: the real function's own source with ONE anchored edit,
re-compiled in memory -- the anchor must occur exactly the expected number of times, so a mutant can never silently
patch nothing) and demonstrates two facts on a real object path:

* ``honest`` -- the unmodified code produces the expected verdict on the fixture;
* ``mutant`` -- the injected bad behaviour produces the BAD verdict on the SAME fixture.

A mutant is KILLED only when BOTH hold. A harness error, an anchor that no longer matches, or a mutant whose bad
behaviour does not show is a SURVIVOR (a real gap), never a ceremonial pass. The harness never edits a byte of
`smartchem/`; every patch is undone on exit.

Round V (F79, honest denominator) -- the output separates three populations and never mixes them:

* ACTIVE -- every mutant whose mechanism exists in the Round-V code (historical mutants PORTED/RE-TARGETED onto the
  successor mechanism when the Round-IV helper was deleted, plus the new Round-V family M63-M94);
* RETIRED -- a historical mutant whose mechanism was DELETED **and** whose bad behaviour is killed by a named Round-V
  replacement mutant (the replacement must itself be ACTIVE and KILLED in the same run, or the retirement is void and
  counted as a survivor);
* DEFERRED / UNCALIBRATED -- a mutant this harness cannot yet run non-vacuously (target: zero).

Run:  .venv/bin/python experiments/v0_9_mutation_calibration.py
"""
from __future__ import annotations

import __future__ as _future
import collections
import contextlib
import dataclasses as dc
import inspect
import json
import os
import sys
import textwrap
import traceback
from fractions import Fraction
from pathlib import Path

import smartchem.capability.assess  # noqa: F401 -- imported for its side effect (populates sys.modules)
import smartchem.capability.declarations as declarations_mod
import smartchem.capability.equipment_resolver as equipment_resolver_mod
import smartchem.capability.presets as presets_mod
import smartchem.capability.profile as profile_mod
import smartchem.capability.requirements as requirements_mod
import smartchem.capability.waste as waste_mod
import smartchem.contracts as contracts_mod
import smartchem.data.derived_evidence as derived_mod
import smartchem.experiment.stock as stock_mod
import smartchem.material_spec as spec_mod
import smartchem.service as svc
from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import AxisResult, assess
from smartchem.capability.enums import (
    MEASUREMENT_TIER_OF,
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    VentilationCapability,
    WasteCapability,
)
from smartchem.capability.presets import (
    custom,
    isopentyl_capability_fit_bench,
    poor_man,
    research_lab,
    resolve_capability_profile,
)
from smartchem.capability.profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile
from smartchem.capability.quantity import QuantityDemand, QuantityKnowledge
from smartchem.capability.requirements import (
    MaterialRequirement,
    RouteCapabilityRequirements,
    WasteRequirement,
    compile_capability_requirements,
)
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.contracts import EvidenceStatus, canonical_digest
from smartchem.data import material_library
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.data.reagents import Availability, commodity_for
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import CareLevel, Fate, RouteHandling, verify_handling
from smartchem.experiment.readiness import (
    CONDITIONS_SUPPORTED,
    FORMAL_CANDIDATE,
    PROCESS_SPECIFIED,
    REACTION_VOUCHED,
    ObligationStatus,
    RouteReadiness,
    StepReadiness,
    evaluate_route,
    tier_rank,
)
from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
from smartchem.experiment.stock import (
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
    HydrationState,
    MaterialSpecification,
    SaturationState,
    StateClaim,
    Tolerance,
)
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.process_constraints import Attention, ProcessBounds, ProcessRequirements
from smartchem.service import (
    CompilationRequest,
    CompilationResponse,
    TransformGrammar,
    build_recompile_request,
    ranked_summary_from_payload,
    request_from_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name

# `smartchem/capability/__init__.py` does `from .assess import ..., assess`, which REBINDS the package's own `assess`
# attribute from the submodule to the FUNCTION -- read the module straight out of `sys.modules` instead.
assess_mod = sys.modules["smartchem.capability.assess"]

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)
_V08 = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "v08"

_MUTANTS: list = []   # (id, title, target, fn)
_RETIRED: list = []   # (id, title, deleted mechanism, reason, replacement ids)
_DEFERRED: list = []  # (id, title, reason) -- target: empty


def mutant(mid: str, title: str, target: str):
    def deco(fn):
        _MUTANTS.append((mid, title, target, fn))
        return fn
    return deco


def retired(mid: str, title: str, mechanism: str, reason: str, replacement: "tuple[str, ...]") -> None:
    _RETIRED.append((mid, title, mechanism, reason, replacement))


@contextlib.contextmanager
def _patch(obj, name, value):
    """Temporarily set ``obj.name = value`` (modules and classes), restoring EXACTLY on exit."""
    had = name in getattr(obj, "__dict__", {})
    old = obj.__dict__.get(name) if had else None
    setattr(obj, name, value)
    try:
        yield
    finally:
        if had:
            setattr(obj, name, old)
        else:
            with contextlib.suppress(AttributeError):
                delattr(obj, name)


@contextlib.contextmanager
def _patch_item(mapping: dict, key, value):
    old = mapping[key]
    mapping[key] = value
    try:
        yield
    finally:
        mapping[key] = old


def _src_mutant(fn, *edits):
    """Re-compile the REAL function ``fn`` from its own source with the given anchored edits applied.

    Each edit is ``(old, new)`` (``old`` must occur EXACTLY once) or ``(old, new, n)`` (exactly ``n`` times) -- a stale
    anchor raises, so a mutant can never silently patch nothing. The copy runs against a snapshot of the defining
    module's globals (so the real module is untouched until the caller installs the result with :func:`_patch`).
    Returns the new function (or the decorated object -- a ``classmethod``/``property`` -- if ``fn`` was decorated)."""
    target = getattr(fn, "__func__", fn)
    src = textwrap.dedent(inspect.getsource(target))
    for edit in edits:
        old, new = edit[0], edit[1]
        expected = edit[2] if len(edit) == 3 else 1
        found = src.count(old)
        if found != expected:
            raise AssertionError(
                f"mutation anchor for {target.__qualname__} found {found}x (expected {expected}): {old!r}")
        src = src.replace(old, new)
    glb = dict(target.__globals__)
    code = compile(src, f"<mutant of {target.__module__}.{target.__qualname__}>", "exec",
                   flags=_future.annotations.compiler_flag, dont_inherit=True)
    exec(code, glb)  # noqa: S102 -- the harness's own re-compilation of in-repo production source
    return glb[target.__name__]


def _status(assessment, axis: str) -> CapabilityStatus:
    return getattr(assessment, axis).status


# =================================================================================================================
# shared plumbing: synthetic requirements/profiles, evidenced bottles, readiness rungs
# =================================================================================================================

def _mol(smiles: str):
    return parse_smiles(smiles)


def _molecule(name: str):
    return structure_by_name(name).molecule


_ETHANOL = _mol("CCO")
_ACETIC = _mol("CC(=O)O")
_METHANOL = _mol("CO")
_WATER = _mol("O")
_ISOAMYL = _mol("CC(C)CCO")


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


def _clean_profile(**over) -> CapabilityProfile:
    """An otherwise-empty profile whose operator declares budget NO_LIMIT (D13): with the synthetic all-clear
    ``_reqs()`` every axis is NOT_APPLICABLE/UNCONSTRAINED/FIT, so the ONLY thing between the fixture and a verdict is
    the mechanism under test."""
    over.setdefault("no_limit_dimensions", frozenset({"budget"}))
    return _profile(**over)


def _readiness_at(tier: str) -> RouteReadiness:
    S, U, UK = ObligationStatus.SATISFIED, ObligationStatus.UNSATISFIED, ObligationStatus.UNKNOWN
    if tier == FORMAL_CANDIDATE:
        step = StepReadiness(formal_candidate=S, reaction_type=U, reaction_class_name=None, conditions=UK,
                             process=UK, workup_isolation=UK, provenance=(),
                             open_obligations=("reaction_type: not recognized",))
    elif tier == REACTION_VOUCHED:
        step = StepReadiness(formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=U,
                             process=UK, workup_isolation=UK, provenance=(),
                             open_obligations=("conditions: not sourced",))
    elif tier == CONDITIONS_SUPPORTED:
        step = StepReadiness(formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=S,
                             process=U, workup_isolation=UK, provenance=("https://example.test/x",),
                             open_obligations=("process: not sourced",))
    elif tier == PROCESS_SPECIFIED:
        step = StepReadiness(formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=S,
                             process=S, workup_isolation=S, provenance=("https://example.test/x",),
                             open_obligations=())
    else:
        raise ValueError(tier)
    assert step.tier == tier, (step.tier, tier)
    return RouteReadiness(per_step=(step,), route_open_obligations=step.open_obligations)


def _ps() -> RouteReadiness:
    return _readiness_at(PROCESS_SPECIFIED)


def _ev(lo: str, hi: str, *, kind: str = "user", basis: ConcentrationBasis = ConcentrationBasis.MASS_FRACTION,
        locator: str = "fixture-locator", domain: str = "fixture interval") -> IntervalEvidence:
    """A real, registry-recomputed IntervalEvidence record (``kind``: user / assumed / quoted / unknown)."""
    if kind == "user":
        return IntervalEvidence.build(
            kernel=DerivationKernel.USER_DECLARED_V1, basis=basis,
            inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                    TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
            domain_of_validity=domain)
    if kind == "assumed":
        return IntervalEvidence.build(
            kernel=DerivationKernel.ASSUMED_BAND_V1, basis=basis,
            inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.ASSUMED),
                    TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.ASSUMED)),
            domain_of_validity=domain)
    if kind == "quoted":
        return IntervalEvidence.build(
            kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, basis=basis,
            inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, locator),
                    TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, locator)),
            source_locators=(locator,), domain_of_validity=domain)
    if kind == "unknown":
        return IntervalEvidence.build(kernel=DerivationKernel.UNKNOWN_V1, basis=basis, domain_of_validity=domain)
    raise ValueError(kind)


def _bottle(mid: str, key, lo: str = "1", hi: str = "1", *, phase: Phase = Phase.LIQUID, qty: "str | None" = "500",
            unit: str = "mL", kind: str = "user", basis: ConcentrationBasis = ConcentrationBasis.MASS_FRACTION,
            states: "tuple[StateClaim, ...]" = (), extra: "tuple[MaterialComponent, ...]" = ()) -> StockMaterial:
    """A single-species StockMaterial keyed by structure (``key`` a Molecule) or declared name (``key`` a str), whose
    interval carries a REAL IntervalEvidence record (``kind='none'`` = no evidence record = UNKNOWN strength). State
    claims are COMPONENT-scoped (Wave-C K1): they describe THIS species in this bottle, never the bottle."""
    if kind == "none":
        comp = (MaterialComponent.of_molecule(key, "active", float(lo), float(hi)) if not isinstance(key, str)
                else MaterialComponent.known(key, "active", float(lo), float(hi)))
        comp = dc.replace(comp, states=tuple(states))
    else:
        comp = MaterialComponent.evidenced(key, "active", _ev(lo, hi, kind=kind, basis=basis), states=tuple(states))
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, mid, mid, (comp,) + tuple(extra), phase, "fixture",
        quantity=None if qty is None else StockQuantity.of(qty, unit),
    )


def _mreq(*, identity=None, name=None, qty: "tuple[tuple[str, str], ...]" = (("mL", "20"),), unstated: int = 0,
          spec: MaterialSpecification = MaterialSpecification(), phase: "Phase | None" = None,
          role: str = "fixture") -> MaterialRequirement:
    return MaterialRequirement(identity=identity, phase=phase, quantity=QuantityDemand(tuple(qty), unstated),
                               role=role, evidence_source="fixture", name=name, specification=spec)


def _comp(lo: str, hi: str, *, basis=ConcentrationBasis.MASS_FRACTION, tol=Tolerance.STATED_INTERVAL,
          ev=EvidenceKind.SOURCE_QUOTED) -> CompositionConstraint:
    return CompositionConstraint(lo, hi, basis, tol, ev)


def _state(state, ev=EvidenceKind.SOURCE_QUOTED) -> StateClaim:
    return StateClaim(state, ev)


def _mat(profile, *reqs) -> CapabilityStatus:
    return assess(profile, _reqs(material=tuple(reqs)), _ps()).material.status


# -- the real searched isopentyl route (cached: the search is deterministic and read-only) --------------------------

_ISO_ROUTE_CACHE: list = []


def _search(target_name, reagents, have, max_depth, tkind=InputKind.NAME):
    target = resolve_target(target_name, tkind).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_route() -> ExperimentRoute:
    """The real, LibreTexts-sourced, PROCESS_SPECIFIED isopentyl-acetate route (the searched object the fit bench and
    tests/test_v0_9_capability_fit_positive.py use). Frozen + cached; every local edit is a `dataclasses.replace` copy."""
    if _ISO_ROUTE_CACHE:
        return _ISO_ROUTE_CACHE[0]
    for route in _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3).routes:
        if any(step.envelope.procedure is not None for step in route.steps):
            _ISO_ROUTE_CACHE.append(route)
            return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


def _map_uses(route: ExperimentRoute, fn) -> ExperimentRoute:
    """A LOCAL copy of ``route`` with every ProcedureMaterialUse passed through ``fn`` (``None`` drops it)."""
    steps = []
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            steps.append(step)
            continue
        ops = []
        for op in procedure.operations:
            uses = tuple(u2 for u2 in (fn(u) for u in op.material_uses) if u2 is not None)
            ops.append(dc.replace(op, material_uses=uses))
        steps.append(dc.replace(step, envelope=dc.replace(step.envelope,
                                                          procedure=dc.replace(procedure, operations=tuple(ops)))))
    return dc.replace(route, steps=tuple(steps))


def _append_use(route: ExperimentRoute, use: ProcedureMaterialUse) -> ExperimentRoute:
    """A LOCAL copy of ``route`` with ``use`` appended to the FIRST procedure operation."""
    steps = list(route.steps)
    for i, step in enumerate(steps):
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        ops = list(procedure.operations)
        ops[0] = dc.replace(ops[0], material_uses=ops[0].material_uses + (use,))
        steps[i] = dc.replace(step, envelope=dc.replace(step.envelope,
                                                        procedure=dc.replace(procedure, operations=tuple(ops))))
        return dc.replace(route, steps=tuple(steps))
    raise AssertionError("expected a procedure-bearing step")


def _fit_inventory_with(**swaps) -> "tuple[StockMaterial, ...]":
    base = {
        "glacial_acetic": material_library.glacial_acetic_acid(quantity=StockQuantity.of("500", "mL")),
        "isoamyl": material_library.isoamyl_alcohol_reagent_grade(quantity=StockQuantity.of("500", "mL")),
        "sulfuric": material_library.concentrated_sulfuric_acid(quantity=StockQuantity.of("500", "mL")),
        "nahco3": material_library.sodium_bicarbonate_wash_5pct(quantity=StockQuantity.of("500", "mL")),
        "nacl": material_library.sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL")),
        "mgso4": material_library.magnesium_sulfate_anhydrous(quantity=StockQuantity.of("250", "g")),
        "water": material_library.wash_water(quantity=StockQuantity.of("1000", "mL")),
    }
    base.update(swaps)
    return tuple(base.values())


def _iso_material(profile, route=None) -> CapabilityStatus:
    route = _isopentyl_route() if route is None else route
    return assess(profile, compile_capability_requirements(route), evaluate_route(route)).material.status


# -- the MICRO route: a real, hand-built, conserving ExperimentRoute whose material axis can genuinely reach FIT ------
# (acetic acid + methanol -> methyl acetate + water, both inputs typed with identity + phase + quantity; no untyped
# strings, no catalyst, no medium). Real ExperimentStep conservation certificate, real procedure evidence. It exists
# so axis-level mutants can show a clean FIT flip on a real compile_capability_requirements path.

_UNK = EvidenceField.unknown()


def _procedure(ops) -> ProcedureEvidence:
    return ProcedureEvidence(reaction_scope="fixture micro-route", source=None, scale=_UNK, operations=tuple(ops),
                             quench=_UNK, workup_isolation=_UNK, separation=_UNK, wash=_UNK, drying=_UNK,
                             purification=_UNK, analytical_verification=_UNK)


def _use(name, role, *, identity=None, qty=None, unit="mL", phase=None, formulation=None, spec=None):
    return ProcedureMaterialUse(name=name, role=role, identity=identity, formulation=formulation, phase=phase,
                                quantity=None if qty is None else StockQuantity.of(qty, unit),
                                evidence_source="fixture micro-route", specification=spec)


_MICRO_BASE_USES = (
    _use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID),
    _use("acetic acid", ProcedureMaterialRole.REACTANT, identity=_ACETIC, qty="10", phase=Phase.LIQUID),
)


def _micro_route(*, extra_uses=(), materials=(), extra_ops=(), base_uses=_MICRO_BASE_USES,
                 **envelope_kw) -> ExperimentRoute:
    op1 = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                             materials=tuple(materials), material_uses=tuple(base_uses) + tuple(extra_uses),
                             locator="fixture")
    ops = [op1] + [dc.replace(op, ordinal=i) for i, op in enumerate(extra_ops, start=2)]
    if any(envelope_kw.get(k) for k in ("temperature", "pressure", "duration", "medium", "catalysts",
                                         "applied_field")):
        # a declared-condition envelope must carry a status above UNSUPPORTED and a provenance (conditions.py law)
        envelope_kw.setdefault("status", EvidenceStatus.EXPERIMENTAL)
        envelope_kw.setdefault("provenance", "fixture micro-route: declared conditions (not a sourced citation)")
    envelope = ConditionEnvelope(procedure=_procedure(ops), **envelope_kw)
    step = ExperimentStep(STEP_SCHEMA, _mol("CC(=O)OC"), (_ACETIC, _METHANOL), (_mol("CC(=O)OC"), _WATER), (),
                          envelope)
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


def _micro_inventory(*extra) -> "tuple[StockMaterial, ...]":
    return (_bottle("methanol-pure", _METHANOL), _bottle("acetic-pure", _ACETIC)) + tuple(extra)


def _micro_profile(*extra_bottles, **over) -> CapabilityProfile:
    over.setdefault("material_inventory", _micro_inventory(*extra_bottles))
    return _clean_profile(**over)


def _micro_assess(route, profile):
    return assess(profile, compile_capability_requirements(route), evaluate_route(route))


def _op(kind, role=OperationRole.OTHER, **kw) -> ProcedureOperation:
    return ProcedureOperation(ordinal=1, kind=kind, role=role, locator="fixture", **kw)


# -- service plumbing -----------------------------------------------------------------------------------------------

_FAST_TARGET = "smiles:CC(=O)OC"  # methyl acetate -- a small, fast max_depth=2 search


def _fit_response():
    req = build_recompile_request(
        "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    return run_compilation(req)


def _dual_profile_runs(profile):
    req_none = build_recompile_request(_FAST_TARGET, max_depth=2)
    resp_none = run_compilation(req_none)
    req_prof = build_recompile_request(_FAST_TARGET, capability_profile=profile, max_depth=2)
    resp_prof = run_compilation(req_prof)
    return req_none, resp_none, req_prof, resp_prof


def _v08(name: str) -> dict:
    return json.loads((_V08 / name).read_text())


# -- flow-algorithm mutants (Round V signature: _max_flow(edges, source, sink) over exact Fractions) ------------------

_REAL_MAX_FLOW = assess_mod._max_flow


def _unlimited_pool_flow(edges, source, sink):
    """The pre-F42 "stock is unlimited" ledger: every source-side demand with ANY path to the sink counts as fully met,
    WITHOUT ever debiting a bottle's shared capacity (a bottle spent as many times as demands reach it)."""
    adj = collections.defaultdict(list)
    for u, v, _c in edges:
        adj[u].append(v)

    def reaches(u, seen):
        if u == sink:
            return True
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                if reaches(v, seen):
                    return True
        return False

    return sum((c for u, v, c in edges if u == source and reaches(v, {source, v})), Fraction(0))


def _single_bottle_flow(edges, source, sink):
    """A flow that FAILS to combine compatible bottles: only the single largest bottle-to-sink capacity counts."""
    caps = [c for _u, v, c in edges if v == sink]
    return max(caps) if caps else Fraction(0)


def _per_species_flow(edges, source, sink):
    """The per-SPECIES-graph bug: each requirement node gets its OWN copy of every bottle's capacity (one multi-
    component package spent once per species graph), and the per-species flows are summed."""
    real = _REAL_MAX_FLOW
    req_nodes = [v for u, v, _c in edges if u == source]
    total = Fraction(0)
    for r in req_nodes:
        sub = [(u, v, c) for (u, v, c) in edges if (u == source and v == r) or u == r or v == sink]
        total += real(sub, source, sink)
    return total


# =================================================================================================================
# M1-M22 (Round II) -- ported onto the Round-V material law (spec_view + compare_specification + D2 allocation)
# =================================================================================================================

@mutant("M1", "commodity-lead-satisfies-material (G- purity read off the UPPER bound)", "assess._edge (pure)")
def m1():
    """A commodity SOURCE LEAD is an UNKNOWN-fraction [0,1] material (section 10.1): even with a declared amount it is
    a POSSIBLE source only, never a proven draw. Honest: UNKNOWN. Mutant: `_edge` reads purity off the optimistic UPPER
    bound of the honestly-unknown interval, so the lead becomes a proven G- source -> FIT."""
    commodity = commodity_for(_molecule("acetic acid"))
    assert commodity is not None
    lead = dc.replace(stock_material_from_commodity(commodity), quantity=StockQuantity.of("500", "mL"))
    req = _mreq(identity=_molecule("acetic acid"))
    profile = _profile(material_inventory=(lead,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, ("pure = (view is not None",
                                              "pure = (view is not None and view.interval[1] == 1) or (view is not None"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M2", "UNKNOWN (straddling) assay treated as sufficient", "material_spec._compare_composition (inside)")
def m2():
    """A certified-evidence bottle whose declared interval STRADDLES the required floor ([0.5, 1.0] vs >= 0.9) must be
    measured, never assumed. Honest: UNDETERMINED -> UNKNOWN. Mutant: 'inside' is judged on the stock's UPPER bound."""
    req = _mreq(identity=_ETHANOL, spec=MaterialSpecification(composition=_comp("0.9", "1", tol=Tolerance.FLOOR)))
    profile = _profile(material_inventory=(_bottle("ethanol-straddle", _ETHANOL, "0.5", "1"),))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_cmp = _src_mutant(spec_mod._compare_composition, ("inside = slo >= rlo and shi <= rhi",
                                                          "inside = shi >= rlo and shi <= rhi"))
    with _patch(spec_mod, "_compare_composition", bad_cmp):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M3", "same-formula isomer satisfies", "stock._structure_key")
def m3():
    """Ethanol never borrows dimethyl ether's (same C2H6O) bottle: the structure key is isomer-proof. Honest: the
    species is absent under the allowed key -> BLOCKED. Mutant: `_structure_key` keys on bare formula -> FIT."""
    dme = _molecule("dimethyl ether")
    assert _ETHANOL.formula == dme.formula

    def run():
        profile = _profile(material_inventory=(_bottle("dme-pure", dme, phase=Phase.GAS),))
        return _mat(profile, _mreq(identity=_ETHANOL))

    honest = run() is CapabilityStatus.BLOCKED
    with _patch(stock_mod, "_structure_key", lambda m: "struct:formula:" + repr(sorted(m.formula.items()))):
        bad = run() is CapabilityStatus.FIT
    return honest, bad


@mutant("M4", "unspecified purity = 100% (absent species assumed present)", "assess._edge (absent)")
def m4():
    """An ungated requirement ABSENT from every declared bottle is a provable negative against a positive demand
    (D2: no G+ edge -> BLOCKED). Mutant: `_edge` fabricates a proven FIT edge for an absent species -> FIT."""
    profile = _profile(material_inventory=(_bottle("acetic-pure", _ACETIC),))
    req = _mreq(identity=_ETHANOL, name="ethanol")
    honest = _mat(profile, req) is CapabilityStatus.BLOCKED
    bad_edge = _src_mutant(assess_mod._edge, (
        "if key is None:\n        return None",
        "if key is None:\n        return _Edge(CapabilityStatus.FIT, True, f\"{stock.material_id}: BUG absent=100%\")"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M5", "equipment fuzzy substring", "equipment_resolver.resolve_apparatus")
def m5():
    probe = "a distillation-adjacent gadget nobody taught this table"
    honest = equipment_resolver_mod.resolve_apparatus(probe) is None

    def bad_resolve(name):
        norm = equipment_resolver_mod._normalize(name)
        hit = equipment_resolver_mod._APPARATUS_ALIASES.get(norm)
        if hit is not None:
            return hit
        return EquipmentCapability.FRACTIONAL_DISTILLATION if "distill" in norm else None

    with _patch(equipment_resolver_mod, "resolve_apparatus", bad_resolve):
        bad = equipment_resolver_mod.resolve_apparatus(probe) is EquipmentCapability.FRACTIONAL_DISTILLATION
    return honest, bad


@mutant("M6", "OUTDOOR clears containment", "assess._membership_axis")
def m6():
    req = _reqs(containment=frozenset({ContainmentCapability.FUME_HOOD}))
    profile = _profile(ventilation=frozenset({VentilationCapability.OUTDOOR}))
    a = assess(profile, req, _ps())
    honest = a.containment.status is CapabilityStatus.BLOCKED and a.overall is CapabilityStatus.BLOCKED
    real = assess_mod._membership_axis

    def bad_membership(required, available, *, axis="", extra_reasons=()):
        if axis == "containment" and VentilationCapability.OUTDOOR in profile.ventilation:
            available = available | {ContainmentCapability.FUME_HOOD}
        return real(required, available, axis=axis, extra_reasons=extra_reasons)

    with _patch(assess_mod, "_membership_axis", bad_membership):
        bad = assess(profile, req, _ps()).containment.status is CapabilityStatus.FIT
    return honest, bad


def _semantic_leak():
    real = CompilationRequest.semantic_digest

    def leaky(self):
        base = real.fget(self)
        return canonical_digest((base, self.capability_profile.profile_digest)) if self.capability_profile else base

    return property(leaky)


@mutant("M7", "profile changes search candidates", "service.CompilationRequest.semantic_digest")
def m7():
    """Search noninterference: the only honest wire to sever is the search-identity pin itself (profile content is
    never in `semantic_digest`). Mutant: the pin absorbs profile content."""
    req_none, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")

    def cand(resp):
        return tuple(c.candidate_digest for c in resp.compilation_ir.candidates)

    honest = cand(resp_none) == cand(resp_prof) and req_none.semantic_digest == req_prof.semantic_digest
    with _patch(CompilationRequest, "semantic_digest", _semantic_leak()):
        bad = req_none.semantic_digest != req_prof.semantic_digest
    return honest, bad


@mutant("M8", "profile changes search receipt", "service.CompilationRequest.semantic_digest")
def m8():
    req_none, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    honest = (resp_none.compilation_ir.search_receipt.digest == resp_prof.compilation_ir.search_receipt.digest
              and req_none.semantic_digest == req_prof.semantic_digest)
    with _patch(CompilationRequest, "semantic_digest", _semantic_leak()):
        bad = req_none.semantic_digest != req_prof.semantic_digest
    return honest, bad


@mutant("M9", "PROCESS_SPECIFIED auto-FIT skips axis check", "assess fold order")
def m9():
    """Real axis evidence (the unmodified `assess()` on the real route under poor_man: BLOCKED), fed to an alternative
    fold that checks the tier BEFORE the axes -- the fold-ORDER bug."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    assert readiness.tier == PROCESS_SPECIFIED
    a = assess(poor_man(), compile_capability_requirements(route), readiness)
    honest = a.overall is CapabilityStatus.BLOCKED

    def bad_fold(axes, tier):
        if tier_rank(tier) >= tier_rank(PROCESS_SPECIFIED):
            return CapabilityStatus.FIT
        return CapabilityStatus.BLOCKED if any(x.status is CapabilityStatus.BLOCKED for x in axes) \
            else CapabilityStatus.UNKNOWN

    return honest, bad_fold(a.axes, readiness.tier) is CapabilityStatus.FIT


@mutant("M10", "CONDITIONS_SUPPORTED -> FIT", "assess.tier_rank (HARD LAW)")
def m10():
    readiness = _readiness_at(CONDITIONS_SUPPORTED)
    honest = assess(_clean_profile(), _reqs(), readiness).overall is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "tier_rank", lambda t: 7):
        bad = assess(_clean_profile(), _reqs(), readiness).overall is CapabilityStatus.FIT
    return honest, bad


@mutant("M11", "unrecognized reaction -> FIT on equipment", "assess.tier_rank (HARD LAW)")
def m11():
    readiness = _readiness_at(FORMAL_CANDIDATE)
    honest = assess(_clean_profile(), _reqs(), readiness).overall is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "tier_rank", lambda t: 7):
        bad = assess(_clean_profile(), _reqs(), readiness).overall is CapabilityStatus.FIT
    return honest, bad


@mutant("M12", "missing verification ignored (assess layer)", "assess._measurement_axis")
def m12():
    route = _isopentyl_route()
    req, readiness = compile_capability_requirements(route), evaluate_route(route)
    honest = assess(poor_man(), req, readiness).measurement.status is CapabilityStatus.BLOCKED

    def bad_axis(required, available, unrecognized):
        return AxisResult(CapabilityStatus.FIT, ("measurement: BUG missing verification ignored",))

    with _patch(assess_mod, "_measurement_axis", bad_axis):
        bad = assess(poor_man(), req, readiness).measurement.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M13", "unknown waste category passes", "assess._membership_axis (waste)")
def m13():
    req = _reqs(waste=WasteRequirement(frozenset({WasteCapability.HAZARDOUS}), ("waste: fixture",)))
    profile = _profile()
    honest = assess(profile, req, _ps()).waste.status is CapabilityStatus.BLOCKED
    real = assess_mod._membership_axis

    def bad_membership(required, available, *, axis="", extra_reasons=()):
        if axis == "waste":
            return AxisResult(CapabilityStatus.FIT, ("waste: BUG passed",))
        return real(required, available, axis=axis, extra_reasons=extra_reasons)

    with _patch(assess_mod, "_membership_axis", bad_membership):
        bad = assess(profile, req, _ps()).waste.status is CapabilityStatus.FIT
    return honest, bad


def _monetary_case(route_cost, budget, mutate):
    req, profile = _reqs(monetary=route_cost), _profile(budget=budget)
    honest = assess(profile, req, _ps()).monetary.status is CapabilityStatus.UNKNOWN
    real = assess_mod._monetary_axis

    def bad(rc, b, **kw):
        out = mutate(rc, b)
        return out if out is not None else real(rc, b, **kw)

    with _patch(assess_mod, "_monetary_axis", bad):
        mutated = assess(profile, req, _ps()).monetary.status is CapabilityStatus.FIT
    return honest, mutated


@mutant("M14", "unknown price = 0", "assess._monetary_axis")
def m14():
    real = assess_mod._monetary_axis

    def mutate(rc, b):
        if rc.cash is None and rc.cash_floor is None:
            return real(dc.replace(rc, cash=0.0, currency="USD", unit="USD"), b)
        return None

    return _monetary_case(CostVector(), CostVector(cash=200.0, currency="USD", unit="USD"), mutate)


@mutant("M15", "cash floor within budget = FIT", "assess._monetary_axis")
def m15():
    def mutate(rc, b):
        if rc.cash is None and rc.cash_floor is not None and b is not None and b.cash is not None \
                and rc.cash_floor <= b.cash:
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG floor treated as total",))
        return None

    return _monetary_case(CostVector(cash_floor=50.0, currency="USD", unit="USD"),
                          CostVector(cash=200.0, currency="USD", unit="USD"), mutate)


@mutant("M16", "mixed currency summed", "assess._monetary_axis")
def m16():
    def mutate(rc, b):
        if b is not None and b.cash is not None and rc.cash is not None and rc.currency != b.currency \
                and rc.cash <= b.cash:
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG mixed currency compared raw",))
        return None

    return _monetary_case(CostVector(cash=50.0, currency="USD", unit="USD"),
                          CostVector(cash=200.0, currency="EUR", unit="USD"), mutate)


@mutant("M17", "unrecognized catalyst = poor-man obtainable", "assess._procurement_axis")
def m17():
    req = _reqs(procurement_catalysts=(("a mystery catalyst nobody has named before", None),))
    profile = _profile(procurement=frozenset(Availability))
    honest = assess(profile, req, _ps()).procurement.status is CapabilityStatus.BLOCKED

    def bad(catalysts, allowed):
        return AxisResult(CapabilityStatus.FIT, ("procurement: BUG unrecognized assumed obtainable",))

    with _patch(assess_mod, "_procurement_axis", bad):
        mutated = assess(profile, req, _ps()).procurement.status is CapabilityStatus.FIT
    return honest, mutated


@mutant("M18", "industrial catalyst free under a kitchen", "assess.is_obtainable_under")
def m18():
    req = _reqs(procurement_catalysts=(("Pd/C", Availability.INDUSTRIAL),))
    profile = _profile(procurement=frozenset({Availability.GROCERY, Availability.HARDWARE}))
    honest = assess(profile, req, _ps()).procurement.status is CapabilityStatus.BLOCKED
    with _patch(assess_mod, "is_obtainable_under", lambda tier, allowed: bool(allowed)):
        bad = assess(profile, req, _ps()).procurement.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M19", "assessment under another profile loads", "service.CompilationResponse._check_capability_coherence")
def m19():
    resp = _fit_response()
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=poor_man()))
    try:
        swapped._check_capability_coherence(require_verified_admission=True)
        honest = False
    except ValueError:
        honest = True
    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            swapped._check_capability_coherence(require_verified_admission=True)
            bad = True
        except ValueError:
            bad = False
    return honest, bad


@mutant("M20", "custom content changes, digest does not", "profile.CapabilityProfile.profile_digest")
def m20():
    p1 = custom(profile_id="x1", equipment=frozenset({EquipmentCapability.BALANCE}))
    p2 = custom(profile_id="x1", equipment=frozenset({EquipmentCapability.REFLUX_CONDENSER}))
    honest = p1.profile_digest != p2.profile_digest
    with _patch(CapabilityProfile, "profile_digest", property(lambda self: "constant")):
        bad = p1.profile_digest == p2.profile_digest
    return honest, bad


@mutant("M21", "one operation's equipment view promotes an under-equipped route",
        "requirements._equipment_requirement (op union)")
def m21():
    """The equipment demand is the UNION over EVERY operation (plus D13 unread hardware ops). The real route's
    whole-step ProcessRequirements.equipment cross-check is stripped in a LOCAL copy to isolate the per-op union.
    Honest: a bench owning only op1's flask BLOCKS. Mutant: only the FIRST operation is scanned -> FIT."""
    base = _isopentyl_route()
    steps = tuple(dc.replace(s, envelope=dc.replace(s.envelope, process=dc.replace(s.envelope.process, equipment=())))
                  if s.envelope.process is not None and s.envelope.process.equipment else s for s in base.steps)
    route = dc.replace(base, steps=steps)
    profile = _profile(equipment=frozenset({EquipmentCapability.REACTION_VESSEL}))
    readiness = evaluate_route(route)
    honest = assess(profile, compile_capability_requirements(route), readiness).equipment.status \
        is CapabilityStatus.BLOCKED
    bad_eq = _src_mutant(requirements_mod._equipment_requirement, (
        "for op in procedure.operations:\n                if op.kind is OperationKind.VERIFY:",
        "for op in procedure.operations[:1]:\n                if op.kind is OperationKind.VERIFY:"))
    with _patch(requirements_mod, "_equipment_requirement", bad_eq):
        bad = assess(profile, compile_capability_requirements(route), readiness).equipment.status \
            is CapabilityStatus.FIT
    return honest, bad


@mutant("M22", "FIT survives readiness demotion", "assess.tier_rank (HARD LAW)")
def m22():
    profile, reqs = _clean_profile(), _reqs()
    honest = (assess(profile, reqs, _ps()).overall is CapabilityStatus.FIT
              and assess(profile, reqs, _readiness_at(REACTION_VOUCHED)).overall is CapabilityStatus.UNKNOWN)
    with _patch(assess_mod, "tier_rank", lambda t: 7):
        bad = assess(profile, reqs, _readiness_at(REACTION_VOUCHED)).overall is CapabilityStatus.FIT
    return honest, bad


# =================================================================================================================
# M23-M40 (Round III + Wave-C)
# =================================================================================================================

retired("M23", "reaction-class label manufactures a universal assay floor",
        "requirements._KNOWN_LEAF_IDS leaf-whitelist floor (deleted by Round IV F45)",
        "no function left to mutate; the bad behaviour (generic compiler knows a special identity / manufactures a "
        "requirement from prose or an adjective table) is killed on the real object path by the replacements",
        ("M55", "M56", "M66"))


@mutant("M24", "procedure-only consumables vanish from material", "requirements._material_requirements")
def m24():
    """Honest: research_lab + the two-reagent lab inventory BLOCKS on the absent, typed MgSO4 drier (positive demand,
    no G+ edge). Mutant: the typed-use projection is skipped -> only bare leaves remain -> the BLOCK vanishes."""
    profile = research_lab(material_inventory=material_library.isopentyl_lab_inventory())
    route = _isopentyl_route()
    a = assess(profile, compile_capability_requirements(route), evaluate_route(route))
    honest = a.material.status is CapabilityStatus.BLOCKED and "magnesium sulfate" in " ".join(a.material.reasons)
    bad_proj = _src_mutant(requirements_mod._material_requirements, (
        "if procedure is None:\n            continue\n        for op in procedure.operations:",
        "if True:\n            continue\n        for op in procedure.operations:"))
    with _patch(requirements_mod, "_material_requirements", bad_proj):
        bad = _iso_material(profile) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M25", "required quantity ignored (unlimited pool)", "assess._max_flow")
def m25():
    """10 mL glacial vs the sourced 20 mL draw: even the optimistic allocation falls short -> BLOCKED. Mutant: the
    pre-F42 unlimited-pool flow -> the provable shortfall launders out of BLOCKED."""
    bench = isopentyl_capability_fit_bench(material_inventory=material_library.isopentyl_insufficient_quantity_inventory())
    honest = _iso_material(bench) is CapabilityStatus.BLOCKED
    with _patch(assess_mod, "_max_flow", _unlimited_pool_flow):
        bad = _iso_material(bench) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M26", "known phase mismatch still passes", "assess._edge (phase gate)")
def m26():
    bench = isopentyl_capability_fit_bench(material_inventory=material_library.isopentyl_wrong_phase_inventory())
    honest = _iso_material(bench) is CapabilityStatus.BLOCKED
    bad_edge = _src_mutant(assess_mod._edge, ("if requirement.phase is not None:", "if False:"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _iso_material(bench) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M27", "required analytical method ignored (requirements layer)", "requirements._measurement_requirement")
def m27():
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    honest = assess(poor_man(), compile_capability_requirements(route), readiness).measurement.status \
        is CapabilityStatus.BLOCKED
    with _patch(requirements_mod, "_measurement_requirement", lambda r: (frozenset(), ())):
        bad = assess(poor_man(), compile_capability_requirements(route), readiness).measurement.status \
            is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M28", "generic tier substitutes for the specific method", "assess._measurement_axis")
def m28():
    req = _reqs(measurement=frozenset({MeasurementMethod.MASS}))
    profile = _profile(measurement=frozenset({MeasurementMethod.MELTING_POINT}))
    honest = assess(profile, req, _ps()).measurement.status is CapabilityStatus.BLOCKED

    def bad_axis(required, available, unrecognized):
        ok = {MEASUREMENT_TIER_OF[m] for m in required} <= {MEASUREMENT_TIER_OF[m] for m in available}
        return AxisResult(CapabilityStatus.FIT if ok else CapabilityStatus.BLOCKED, ("measurement: BUG tier-only",))

    with _patch(assess_mod, "_measurement_axis", bad_axis):
        bad = assess(profile, req, _ps()).measurement.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M29", "UNCONSTRAINED with a real demand silently FITs", "assess._physical_axis")
def m29():
    req = _reqs(physical=PhysicalBounds.of(max_temperature_k=416.15))
    a = assess(_clean_profile(), req, _ps())
    honest = a.physical.status is CapabilityStatus.UNKNOWN and a.overall is CapabilityStatus.UNKNOWN
    real = assess_mod._physical_axis

    def bad_axis(requirement, ceiling, **kw):
        if not ceiling.constrains_anything:
            return AxisResult(CapabilityStatus.UNCONSTRAINED, ("physical: BUG unconstrained regardless",))
        return real(requirement, ceiling, **kw)

    with _patch(assess_mod, "_physical_axis", bad_axis):
        bad = assess(_clean_profile(), req, _ps()).overall is CapabilityStatus.FIT
    return honest, bad


def _unit_mismatch_mutate(rc, b):
    if b is not None and b.cash is not None and rc.cash is not None and rc.unit != b.unit and rc.cash <= b.cash:
        return AxisResult(CapabilityStatus.FIT, ("monetary: BUG unit mismatch compared raw",))
    return None


@mutant("M30", "budget compares different CostVector units", "assess._monetary_axis")
def m30():
    return _monetary_case(CostVector(cash=5.0, currency="USD", unit="metric ton"),
                          CostVector(cash=200.0, currency="USD", unit="USD"), _unit_mismatch_mutate)


@mutant("M31", "per-mol cost compared to a total budget", "assess._monetary_axis")
def m31():
    return _monetary_case(CostVector(cash=3.0, currency="USD", unit="mol-product"),
                          CostVector(cash=200.0, currency="USD", unit="USD"), _unit_mismatch_mutate)


@mutant("M32", "ventilation silently claims an assessed axis", "assess._ventilation_axis")
def m32():
    a = assess(_profile(), _reqs(), _ps())
    honest = a.ventilation.status is CapabilityStatus.NOT_APPLICABLE and "RESERVED" in " ".join(a.ventilation.reasons)
    with _patch(assess_mod, "_ventilation_axis", lambda: AxisResult(CapabilityStatus.FIT, ("ventilation: BUG",))):
        m = assess(_profile(), _reqs(), _ps())
        bad = m.ventilation.status is CapabilityStatus.FIT and "RESERVED" not in " ".join(m.ventilation.reasons)
    return honest, bad


@mutant("M33", "procedure-only hazardous material omitted from containment", "requirements._hazard_scan")
def m33():
    """The real H2SO4 catalyst (H314) names itself in the containment reasons and the unresolvable ionic washes are
    surfaced as hazard_unresolved (inform, never neuter). Mutant: the scan reports nothing -> the named evidence
    vanishes from the requirement AND from the assessed containment reasons."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    honest = (req.containment == frozenset({ContainmentCapability.FUME_HOOD})
              and "sulfuric acid" in " ".join(req.containment_reasons) and "H314" in " ".join(req.containment_reasons)
              and any("sodium bicarbonate" in r for r in req.hazard_unresolved))
    with _patch(requirements_mod, "_hazard_scan", lambda r, untyped: (False, (), ())):
        req2 = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    bench = isopentyl_capability_fit_bench()
    bad = (req2.containment_reasons == () and req2.hazard_unresolved == ()
           and "sulfuric acid" in " ".join(assess(bench, req, readiness).containment.reasons)
           and "sulfuric acid" not in " ".join(assess(bench, req2, readiness).containment.reasons))
    return honest, bad


@mutant("M34", "named-preset request stores only the name", "presets.CAPABILITY_PROFILE_PRESETS (re-resolve)")
def m34():
    req = build_recompile_request(_FAST_TARGET, capability_profile="poor-man", max_depth=2)
    snapshot = req.capability_profile
    assert snapshot is not None and req.capability_profile_origin == "poor-man"
    drifted = custom(profile_id="poor-man", equipment=frozenset({EquipmentCapability.BALANCE}))
    presets = dict(presets_mod.CAPABILITY_PROFILE_PRESETS)
    presets["poor-man"] = lambda: drifted
    with _patch(presets_mod, "CAPABILITY_PROFILE_PRESETS", presets):
        honest = req.capability_profile == snapshot
        bad = resolve_capability_profile(req.capability_profile_origin) != snapshot
    return honest, bad


@mutant("M35", "custom content changes without capability_question_digest moving",
        "service.CompilationRequest.capability_question_digest")
def m35():
    p1 = custom(profile_id="a", equipment=frozenset({EquipmentCapability.BALANCE}))
    p2 = custom(profile_id="a", equipment=frozenset({EquipmentCapability.REFLUX_CONDENSER}))
    r1 = build_recompile_request(_FAST_TARGET, capability_profile=p1, max_depth=2)
    r2 = build_recompile_request(_FAST_TARGET, capability_profile=p2, max_depth=2)
    honest = r1.capability_question_digest != r2.capability_question_digest and r1.semantic_digest == r2.semantic_digest
    with _patch(CompilationRequest, "capability_question_digest",
                property(lambda self: None if self.capability_profile is None else self.semantic_digest)):
        bad = r1.capability_question_digest == r2.capability_question_digest
    return honest, bad


@mutant("M36", "profile selection changes the search question identity", "service.CompilationRequest.semantic_digest")
def m36():
    req_none, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    honest = (req_none.semantic_digest == req_prof.semantic_digest
              and resp_none.search_space_status == resp_prof.search_space_status)
    with _patch(CompilationRequest, "semantic_digest", _semantic_leak()):
        bad = req_none.semantic_digest != req_prof.semantic_digest
    return honest, bad


@mutant("M37", "no-profile request silently receives a bench assumption",
        "service.CompilationResponse._check_capability_coherence")
def m37():
    _, resp_none, _, resp_prof = _dual_profile_runs("poor-man")
    ok_none = all(d.capability_assessment is None for d in resp_none.ranked_route_dossiers)
    forged = next(d.capability_assessment for d in resp_prof.ranked_route_dossiers if d.capability_assessment)
    dossiers = list(resp_none.ranked_route_dossiers)
    dossiers[0] = dc.replace(dossiers[0], capability_assessment=forged)
    forged_resp = dc.replace(resp_none, ranked_route_dossiers=tuple(dossiers))
    try:
        forged_resp._check_capability_coherence(require_verified_admission=True)
        refuses = False
    except ValueError:
        refuses = True
    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            forged_resp._check_capability_coherence(require_verified_admission=True)
            bad = True
        except ValueError:
            bad = False
    return ok_none and refuses, bad


@mutant("M38", "canonical assessment loads after its evidence (declared stock) is altered",
        "service.CompilationResponse._check_capability_coherence")
def m38():
    """Round V: the real searched isopentyl bench is overall UNKNOWN and its material axis UNKNOWN too, but the carried
    per-route assessment's material reasons REST ON the declared stock (named bottles). Stripping the stock from the
    carried profile snapshot (pin forged consistently, so only CAPABILITY-REBIND-ON-LOAD can catch it) must be REFUSED;
    the mutant disables the re-derivation and the stale assessment loads."""
    resp = _fit_response()
    assert any(d.capability_assessment and "glacial-acetic-acid" in " ".join(d.capability_assessment.material.reasons)
               for d in resp.ranked_route_dossiers)
    payload = response_to_payload(resp)
    cp = payload["request"]["capability_profile"]
    for f in cp["fields"]:
        if f[0] == "material_inventory":
            f[1]["items"] = []
    tampered = svc._capability_profile_from_payload(cp)
    payload["capability_question_digest"] = canonical_digest((resp.request.semantic_digest, tampered.profile_digest))
    try:
        response_from_payload(payload)
        honest = False
    except ValueError:
        honest = True
    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            response_from_payload(payload)
            bad = True
        except ValueError:
            bad = False
    return honest, bad


@mutant("M39", "partial physical ceiling drops an undeclared-but-demanded dimension", "assess._physical_axis")
def m39():
    req = _reqs(physical=PhysicalBounds.of(max_pressure_atm=100.0))
    profile = _profile(physical_bounds=PhysicalBounds.of(max_temperature_k=500.0))
    honest = assess(profile, req, _ps()).physical.status is CapabilityStatus.UNKNOWN

    def bad_axis(requirement, ceiling, **kw):
        blocked = any(c is not None and d is not None and (d < c if floor else d > c) for d, c, floor in (
            (requirement.max_temperature_k, ceiling.max_temperature_k, False),
            (requirement.max_pressure_atm, ceiling.max_pressure_atm, False),
            (requirement.min_pressure_atm, ceiling.min_pressure_atm, True)))
        return AxisResult(CapabilityStatus.BLOCKED if blocked else CapabilityStatus.FIT, ("physical: BUG",))

    with _patch(assess_mod, "_physical_axis", bad_axis):
        bad = assess(profile, req, _ps()).physical.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M40", "empty-denominator cost wildcards to FIT", "assess._monetary_axis")
def m40():
    def mutate(rc, b):
        if b is None or b.cash is None or rc.cash is None:
            return None
        if (rc.currency and b.currency and rc.currency != b.currency) or (rc.unit and b.unit and rc.unit != b.unit):
            return None
        return AxisResult(CapabilityStatus.FIT, ("monetary: BUG empty denominator wildcarded",)) \
            if rc.cash <= b.cash else None

    return _monetary_case(CostVector(cash=5.0, currency="", unit=""),
                          CostVector(cash=200.0, currency="USD", unit="USD"), mutate)


# =================================================================================================================
# M41-M62 (Round IV) -- ported / re-targeted / retired against Round V
# =================================================================================================================

@mutant("M41", "repeated use keeps the first draw, not the whole-route sum",
        "quantity.QuantityDemand.combine (successor of the deleted _sum_commensurable)")
def m41():
    """water: 55 + 10 + 25 = 90 mL whole-route demand. Honest: an 80 mL water bottle -> BLOCKED. Mutant: the monoid
    fold keeps only the FIRST draw (55 mL) -> the provable shortfall disappears."""
    bench = isopentyl_capability_fit_bench(
        material_inventory=_fit_inventory_with(water=material_library.wash_water(quantity=StockQuantity.of("80", "mL"))))
    honest = _iso_material(bench) is CapabilityStatus.BLOCKED
    real = QuantityDemand.__dict__["combine"].__func__

    def first_wins(cls, uses):
        uses = list(uses)
        first = next((u for u in uses if u is not None), None)
        return real(cls, [first] if first is not None else uses)

    with _patch(QuantityDemand, "combine", classmethod(first_wins)):
        bad = _iso_material(bench) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M42", "one finite bottle satisfies two independent demands", "assess._max_flow")
def m42():
    bottle = _bottle("ethanol-30ml", _ETHANOL, qty="30")
    reqs = (_mreq(identity=_ETHANOL, role="draw A"), _mreq(identity=_ETHANOL, role="draw B"))
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, *reqs) is CapabilityStatus.BLOCKED
    with _patch(assess_mod, "_max_flow", _unlimited_pool_flow):
        bad = _mat(profile, *reqs) is CapabilityStatus.FIT
    return honest, bad


@mutant("M43", "compatible bottles fail to combine toward one demand", "assess._max_flow")
def m43():
    bottles = tuple(_bottle(f"ethanol-25ml-{i}", _ETHANOL, qty="25") for i in (1, 2))
    req = _mreq(identity=_ETHANOL, qty=(("mL", "40"),))
    profile = _profile(material_inventory=bottles)
    honest = _mat(profile, req) is CapabilityStatus.FIT
    with _patch(assess_mod, "_max_flow", _single_bottle_flow):
        bad = _mat(profile, req) is CapabilityStatus.BLOCKED
    return honest, bad


def _unsaturated_brine() -> StockMaterial:
    return _bottle("nacl-dilute-unsaturated", "sodium chloride", "0.02", "0.03", phase=Phase.AQUEOUS_SOLUTION,
                   qty="250", states=(_state(SaturationState.UNSATURATED, EvidenceKind.USER_DECLARED),
                                      _state(DilutionState.SOLUTION, EvidenceKind.USER_DECLARED)))


@mutant("M44", "typed source specification erased before assessment",
        "requirements._project_specification (successor of the deleted _formulation_spec)")
def m44():
    """Honest: the real route's source-typed SATURATED brine demand vs a bottle the bench POSITIVELY declares
    UNSATURATED -> VIOLATES -> no G+ edge -> BLOCKED. Mutant: the projection erases the typed specification -> the
    dilute bottle passes as a possible source -> the BLOCK vanishes."""
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(nacl=_unsaturated_brine()))
    honest = _iso_material(bench) is CapabilityStatus.BLOCKED
    bad_proj = _src_mutant(requirements_mod._project_specification, (
        "if use.specification is not None:\n        return use.specification",
        "if use.specification is not None:\n        return _EMPTY_SPEC"))
    with _patch(requirements_mod, "_project_specification", bad_proj):
        bad = _iso_material(bench) is not CapabilityStatus.BLOCKED
    return honest, bad


retired("M45", "hydrated drier satisfies anhydrous",
        "StockMaterial.satisfies_band inside the capability fold (deleted from the capability path by Round V D3/D5)",
        "anhydrous is now a positive hydration-STATE claim, never an assay band; the same bad behaviour (a hydrate "
        "passing as ANHYDROUS on its assay number) is killed by M68, and a contrary declaration by M47's successor M67 "
        "family / the VIOLATES->BLOCKED map (M46b)", ("M68", "M46b"))


@mutant("M46", "over-concentrated stock satisfies a 5% band (ceiling dropped)",
        "material_spec._compare_composition (successor of satisfies_band's ceiling)")
def m46():
    req = _mreq(name="sodium bicarbonate", qty=(("mL", "50"),),
                spec=MaterialSpecification(composition=_comp("0.045", "0.055")))
    profile = _profile(material_inventory=(
        _bottle("nahco3-overconc", "sodium bicarbonate", "0.99", "1", phase=Phase.AQUEOUS_SOLUTION),))
    honest = _mat(profile, req) is CapabilityStatus.BLOCKED
    bad_cmp = _src_mutant(spec_mod._compare_composition, ("inside = slo >= rlo and shi <= rhi", "inside = slo >= rlo"))
    with _patch(spec_mod, "_compare_composition", bad_cmp):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M46b", "a certified VIOLATES folds to UNKNOWN (contrary declaration ignored)", "assess._SPEC_TO_STATUS")
def m46b():
    """Honest: the real route's SATURATED brine demand vs a bench-declared UNSATURATED brine -> VIOLATES -> BLOCKED.
    Mutant: the spec->status map folds VIOLATES to UNKNOWN (a proven contrary claim treated as an open question)."""
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(nacl=_unsaturated_brine()))
    honest = _iso_material(bench) is CapabilityStatus.BLOCKED
    bad_map = dict(assess_mod._SPEC_TO_STATUS)
    bad_map[spec_mod.SpecVerdict.VIOLATES] = CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "_SPEC_TO_STATUS", bad_map):
        bad = _iso_material(bench) is not CapabilityStatus.BLOCKED
    return honest, bad


retired("M47", "unsaturated stock satisfies a saturated brine",
        "StockMaterial.satisfies_band floor inside the capability fold (deleted from the capability path by Round V D5)",
        "saturation is a positive STATE claim, never a numeric floor; the bad behaviour (a sub-saturated stock passing "
        "as SATURATED) is killed by M67 (numeric threshold discharges SATURATED) and M46b (a certified contrary "
        "UNSATURATED declaration folded away)", ("M67", "M46b"))


@mutant("M48", "structure-known requirement FITs name-only stock", "assess._species_key_in")
def m48():
    profile = _profile(material_inventory=(_bottle("ethanol-name-only", "ethanol"),))
    req = _mreq(identity=_ETHANOL, name="ethanol")
    honest = _mat(profile, req) is CapabilityStatus.BLOCKED

    def bad_key(r, stock):
        if r.identity is not None and stock.active_fraction_interval(r.identity) is not None:
            return r.identity
        if r.name is not None and stock.active_fraction_interval(r.name) is not None:
            return r.name
        return None

    with _patch(assess_mod, "_species_key_in", bad_key):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M49", "hazard-unresolved displayed but containment FIT", "requirements._hazard_scan (unresolved leg)")
def m49():
    route = _isopentyl_route()
    readiness, bench = evaluate_route(route), isopentyl_capability_fit_bench()
    honest = assess(bench, compile_capability_requirements(route), readiness).containment.status \
        is CapabilityStatus.UNKNOWN
    real = requirements_mod._hazard_scan

    def drop_unresolved(r, untyped):
        forces, reasons, _unresolved = real(r, untyped)
        return forces, reasons, ()

    with _patch(requirements_mod, "_hazard_scan", drop_unresolved):
        bad = assess(bench, compile_capability_requirements(route), readiness).containment.status \
            is CapabilityStatus.FIT
    return honest, bad


def _handling_with_byproducts(route, **byproduct_over):
    """The REAL RouteHandling of ``route`` with every byproduct entry rewritten via ``dataclasses.replace`` (a valid
    ByproductEntry/StepHandling/RouteHandling domain object, re-validated by their own __post_init__)."""
    real = verify_handling(route)
    steps = tuple(dc.replace(sh, byproducts=tuple(dc.replace(b, **byproduct_over) for b in sh.byproducts))
                  for sh in real.steps)
    forged = RouteHandling(steps)
    assert forged.all_byproducts, "fixture needs at least one byproduct"
    return forged


def _waste_flip(route, handling, mutated_derive, honest_marker: str):
    """Shared M50/M78 discriminator on the REAL derive_waste path (verify_handling is the real call it makes):
    derive_waste output + the assessed waste axis under a bench that routes HAZARDOUS but NOT AQUEOUS_NEUTRAL."""
    bench = dc.replace(isopentyl_capability_fit_bench(), waste_handling=frozenset({WasteCapability.HAZARDOUS}))
    readiness = evaluate_route(route)
    with _patch(waste_mod, "verify_handling", lambda r, **kw: handling):
        cats, _reasons, unresolved = waste_mod.derive_waste(route)
        honest_axis = assess(bench, compile_capability_requirements(route), readiness).waste.status
        bad_derive = mutated_derive()
        m_cats, _m_reasons, m_unresolved = bad_derive(route)
        with _patch(waste_mod, "derive_waste", bad_derive):
            mutant_axis = assess(bench, compile_capability_requirements(route), readiness).waste.status
    honest = (WasteCapability.AQUEOUS_NEUTRAL not in cats and any(honest_marker in u for u in unresolved)
              and honest_axis is CapabilityStatus.UNKNOWN)
    bad = (WasteCapability.AQUEOUS_NEUTRAL in m_cats and not any(honest_marker in u for u in m_unresolved)
           and mutant_axis is CapabilityStatus.BLOCKED)
    return honest, bad


@mutant("M50", "unassessed condensed byproduct becomes AQUEOUS_NEUTRAL (benign by negation)",
        "waste.derive_waste (hazard_name is None branch)")
def m50():
    """CLOSED in Round V (was VERIFIED-DEFER). Fixture: the real isopentyl route + its REAL RouteHandling with the
    water byproduct rewritten to an UNASSESSED (hazard_name=None) CONDENSED co-product -- a valid domain object served
    through the real `verify_handling` call derive_waste makes. Honest: the byproduct lands in `unresolved` ("NO hazard
    assessment"), never a category; the waste axis is UNKNOWN. Mutant: the unassessed stream is classified
    AQUEOUS_NEUTRAL by negation -> the category appears, the unresolved line vanishes, and a bench without an
    AQUEOUS_NEUTRAL route now reads BLOCKED on a stream nobody assessed."""
    route = _isopentyl_route()
    handling = _handling_with_byproducts(route, hazard_name=None, fate=Fate.CONDENSED,
                                         reason="fixture: condensed co-product, hazard UNASSESSED")

    def mutated():
        return _src_mutant(waste_mod.derive_waste, (
            'unresolved.add(f"waste: {label} has NO hazard assessment',
            'categories.add(WasteCapability.AQUEOUS_NEUTRAL) or (f"waste: {label} has NO hazard assessment'))

    return _waste_flip(route, handling, mutated, "NO hazard assessment")


@mutant("M51", "spent workup streams omitted -> waste FIT", "requirements._waste_requirement")
def m51():
    route = _isopentyl_route()
    readiness, bench = evaluate_route(route), isopentyl_capability_fit_bench()
    honest = assess(bench, compile_capability_requirements(route), readiness).waste.status is CapabilityStatus.UNKNOWN
    real = requirements_mod._waste_requirement
    with _patch(requirements_mod, "_waste_requirement",
                lambda r: WasteRequirement(real(r).categories, real(r).reasons, ())):
        bad = assess(bench, compile_capability_requirements(route), readiness).waste.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M52", "two distinct specs of one species deduped by identity", "requirements._material_requirements (key)")
def m52():
    extra = _use("acetic acid", ProcedureMaterialRole.WASH, identity=_ACETIC, qty="25", phase=Phase.AQUEOUS_SOLUTION,
                 formulation="5% aqueous", spec=MaterialSpecification(
                     composition=_comp("0.045", "0.055"), states=(_state(DilutionState.SOLUTION),)))
    route = _append_use(_isopentyl_route(), extra)
    bench = isopentyl_capability_fit_bench()
    honest = _iso_material(bench, route) is CapabilityStatus.BLOCKED
    bad_proj = _src_mutant(requirements_mod._material_requirements, (
        "key = (species_key, canonical_digest(spec), use.phase)", "key = species_key"))
    with _patch(requirements_mod, "_material_requirements", bad_proj):
        bad = _iso_material(bench, route) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M53", "DAG capability request accepted but unassessed", "service._run_recompile (convergent+profile refusal)")
def m53():
    """A NEGATIVE property with no severable helper (an inline guard): proved by the counterfactual it prevents --
    the SAME convergent search without the guard's trigger proceeds and answers the capability question with nothing."""
    kw = dict(grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, helper_reagents=("water", "acetic acid"),
              stock_materials=("isopentyl alcohol",))
    resp_p = run_compilation(build_recompile_request("isopentyl acetate",
                                                     capability_profile=isopentyl_capability_fit_bench(), **kw))
    honest = resp_p.outcome.value == "REFUSED" and any(
        "capab" in d.lower() and "convergent" in d.lower() for d in resp_p.diagnostics)
    resp_u = run_compilation(build_recompile_request("isopentyl acetate", **kw))
    bad = resp_u.outcome.value != "REFUSED" and all(
        getattr(d, "capability_assessment", None) is None for d in resp_u.ranked_route_dossiers)
    return honest, bad


@mutant("M54", "compile human render drops capability while JSON honors it", "service.render_capability_lines")
def m54():
    from smartchem.cli import _render_recompile_response
    resp = _fit_response()
    json_has = any(d.get("capability_assessment") for d in response_to_payload(resp)["ranked_route_dossiers"])
    honest = "CAPABILITY[" in _render_recompile_response(resp, quiet=False) and json_has
    with _patch(svc, "render_capability_lines", lambda assessment, origin, *, indent: []):
        bad = "CAPABILITY[" not in _render_recompile_response(resp, quiet=False) and json_has
    return honest, bad


def _deformulated_acetic_route() -> ExperimentRoute:
    """The real route with the acetic-acid REACTANT use's raw formulation AND typed specification cleared (a LOCAL
    copy): the compiler then has no sourced constraint on it. The procedure PROSE still says 'glacial'."""
    return _map_uses(_isopentyl_route(), lambda u: dc.replace(u, formulation=None, specification=None)
                     if u.name == "acetic acid" else u)


def _acetic_90() -> StockMaterial:
    return _bottle("acetic-90pct", _ACETIC, "0.9", "0.92")


def _floor_spec(lo: str) -> MaterialSpecification:
    return MaterialSpecification(composition=_comp(lo, "1", tol=Tolerance.FLOOR))


@mutant("M55", "generic compiler knows a special reagent identity", "requirements._material_requirements")
def m55():
    route = _deformulated_acetic_route()
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(glacial_acetic=_acetic_90()))
    honest = _iso_material(bench, route) is not CapabilityStatus.BLOCKED
    acetic_key = requirements_mod._struct_digest(_ACETIC)
    real = requirements_mod._material_requirements

    def identity_floor(r_):
        return tuple(dc.replace(r, specification=_floor_spec("0.98"))
                     if r.identity is not None and requirements_mod._struct_digest(r.identity) == acetic_key else r
                     for r in real(r_))

    with _patch(requirements_mod, "_material_requirements", identity_floor):
        bad = _iso_material(bench, route) is CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M56", "runtime 'glacial' prose scan manufactures a requirement", "requirements._material_requirements")
def m56():
    route = _deformulated_acetic_route()
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(glacial_acetic=_acetic_90()))
    honest = _iso_material(bench, route) is not CapabilityStatus.BLOCKED
    real = requirements_mod._material_requirements

    def prose(r_):
        chunks = []
        for step in r_.steps:
            p = step.envelope.procedure
            if p is None:
                continue
            if isinstance(p.scale.value, str):
                chunks.append(p.scale.value)
            for op in p.operations:
                if op.quantity is not None and isinstance(op.quantity.value, str):
                    chunks.append(op.quantity.value)
        return " ".join(chunks).casefold()

    def prose_scan(r_):
        glacial = "glacial" in prose(r_)
        return tuple(dc.replace(r, specification=_floor_spec("0.99"))
                     if glacial and r.name is not None and "acetic acid" in r.name.casefold() else r for r in real(r_))

    with _patch(requirements_mod, "_material_requirements", prose_scan):
        bad = _iso_material(bench, route) is CapabilityStatus.BLOCKED
    return honest, bad


_PC_NACL = "https://pubchem.ncbi.nlm.nih.gov/compound/5234 (fixture copy)"


def _solubility_inputs(value: str, unit: InputUnit):
    return (TypedInput("low", value, unit, EvidenceKind.SOURCE_QUOTED, _PC_NACL, "298.15"),
            TypedInput("high", value, unit, EvidenceKind.SOURCE_QUOTED, _PC_NACL, "298.15"))


@mutant("M57", "solubility (g/100 g water) used AS a mass fraction", "derived_evidence.IntervalEvidence.recompute")
def m57():
    """Re-targeted from the deleted DerivedIntervalEvidence onto its successor's load-bearing check: construction
    RE-COMPUTES the interval through the registered kernel. Honest: the correct 36/136 record builds and verifies; the
    36.0 g/100 g figure dropped straight into the slots as 0.36 is REFUSED. Mutant: recompute trusts the stated value
    -> the mislabelled record constructs."""
    honest_rec = IntervalEvidence.build(
        kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=_solubility_inputs("36.0", InputUnit.G_PER_100G_SOLVENT), source_locators=(_PC_NACL,),
        domain_of_validity="aqueous NaCl at saturation, 25 C")

    def bad_record():
        return IntervalEvidence(EvidenceKind.DERIVED, "0.36", "0.36", ConcentrationBasis.MASS_FRACTION, (_PC_NACL,),
                                DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                                _solubility_inputs("36.0", InputUnit.G_PER_100G_SOLVENT),
                                "aqueous NaCl at saturation, 25 C")

    try:
        bad_record()
        refused = False
    except ValueError:
        refused = True
    honest = honest_rec.verify() and honest_rec.low.startswith("0.2647") and refused
    with _patch(IntervalEvidence, "recompute", lambda self: self.interval):
        try:
            bad = bad_record().low == "0.36"
        except ValueError:
            bad = False
    return honest, bad


retired("M58", "decorative uncertainty labelled as a measured/derived method",
        "DerivedIntervalEvidence free DerivationMethod label (deleted by Round V D7)",
        "labels are now bound to a CLOSED kernel registry (a label can no longer claim more than its arithmetic); the "
        "Round-IV M58 RESIDUAL (mislabelled-but-arithmetically-consistent width) is now REFUSED at construction and "
        "killed by M74; the arithmetic-width leg is the same recompute guard M57 kills", ("M74", "M57"))


@mutant("M59", "legacy v0.8 dossier decoder fabricates capability",
        "service._capability_assessment_from_payload (legacy seam)")
def m59():
    """Now on a REAL v0.8 artifact (main@df1b38d fixture), not a key-stripped 0.9 payload: a genuine
    ranked-route-summary-v1alpha3 dossier decodes with capability NOT_REQUESTED. Mutant: the decoder fabricates an
    assessment for the absent field -- surfaced, or (defence in depth) refused by RankedRouteSummary's own legacy
    guard; either way the genuine v0.8 artifact no longer decodes as NOT_REQUESTED."""
    dossier = _v08("response_isopentyl_acetate.json")["ranked_route_dossiers"][0]
    honest = ranked_summary_from_payload(dossier).capability_assessment is None
    fabricated = assess(_clean_profile(), _reqs(), _ps())
    real = svc._capability_assessment_from_payload
    with _patch(svc, "_capability_assessment_from_payload", lambda p: fabricated if p is None else real(p)):
        try:  # detected either way: a fabricated assessment surfaces, or the record's own legacy guard refuses it
            bad = ranked_summary_from_payload(dossier).capability_assessment is not None
        except ValueError as exc:
            bad = "cannot carry a capability_assessment" in str(exc)
    return honest, bad


def _omit_field_encoder(cls, field_name):
    """A mutant `contracts.canonical_payload` whose dataclass branch SKIPS ``cls.field_name`` (the encoder is recursive
    through its module global, so nested records are covered too)."""
    real = contracts_mod.canonical_payload

    def encoder(value):
        if type(value) is cls:
            return {"type": "dataclass", "class": f"{cls.__module__}.{cls.__qualname__}",
                    "fields": [[f.name, encoder(getattr(value, f.name))] for f in dc.fields(value)
                               if f.compare and not f.name.startswith("_") and f.name != field_name]}
        return real(value)

    return encoder


@mutant("M60", "source-substituted use stays digest-identical", "contracts.canonical_payload (evidence_source)")
def m60():
    r1 = MaterialRequirement(identity=None, name="acetic acid", phase=None, quantity=QuantityDemand.unstated(1),
                             role="reactant", evidence_source="LibreTexts isopentyl-acetate experiment, op 1")
    r2 = dc.replace(r1, evidence_source="a DIFFERENT, substituted source citation")
    honest = canonical_digest(r1) != canonical_digest(r2)
    with _patch(contracts_mod, "canonical_payload", _omit_field_encoder(MaterialRequirement, "evidence_source")):
        bad = canonical_digest(r1) == canonical_digest(r2)
    return honest, bad


_TIME_BOUNDS = ProcessBounds.of(max_step_minutes=1000.0, max_total_minutes=1000.0)


@mutant("M61", "partial ProcessBounds launders an unmet ACTIVE-time demand", "assess._PROCESS_TIME_DIMENSIONS")
def m61():
    req = ProcessRequirements(workup_included=True, provenance="fixture",
                              elapsed_minutes=Interval(0, 60, "min"), active_minutes=Interval(0, 30, "min"))
    profile = _profile(process_bounds=_TIME_BOUNDS)  # step + total time DECLARED, active UNDECLARED
    honest = assess_mod._process_axis((req,), profile).status is CapabilityStatus.UNKNOWN
    table = assess_mod._PROCESS_TIME_DIMENSIONS
    assert table[-1][2] == "max_active_minutes"
    with _patch(assess_mod, "_PROCESS_TIME_DIMENSIONS", table[:-1]):
        bad = assess_mod._process_axis((req,), profile).status is CapabilityStatus.FIT
    return honest, bad


@mutant("M62", "attention/agitation dropped from the process fail-close table", "assess._PROCESS_FAILCLOSE_DIMENSIONS")
def m62():
    req = ProcessRequirements(attention=Attention.CONTINUOUS, workup_included=True, provenance="fixture",
                              elapsed_minutes=Interval(0, 60, "min"))
    profile = _clean_profile(process_bounds=_TIME_BOUNDS)
    honest = (assess_mod._process_axis((req,), profile).status is CapabilityStatus.UNKNOWN
              and assess(profile, _reqs(process=(req,)), _ps()).overall is CapabilityStatus.UNKNOWN)
    table = assess_mod._PROCESS_FAILCLOSE_DIMENSIONS
    assert [label for label, _r, _b in table][-2:] == ["attention mode", "agitation mode"]
    with _patch(assess_mod, "_PROCESS_FAILCLOSE_DIMENSIONS", table[:-2]):
        bad = (assess_mod._process_axis((req,), profile).status is CapabilityStatus.FIT
               and assess(profile, _reqs(process=(req,)), _ps()).overall is CapabilityStatus.FIT)
    return honest, bad


# =================================================================================================================
# M63-M82 (Round V family: quantity / allocation / specification / evidence / waste / schema / declaration)
# =================================================================================================================

@mutant("M63", "known + unknown quantity collapses to EXACT (F64)", "quantity.QuantityDemand.combine")
def m63():
    """Real micro-route projection: methanol drawn twice, once unquantified -> LOWER_BOUND_PLUS_UNKNOWN -> material
    UNKNOWN. Mutant: the fold drops the unquantified use (the Round-IV `sum(non-None)` bug) -> EXACT 10 mL -> FIT."""
    route = _micro_route(extra_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL,
                                          phase=Phase.LIQUID),))
    reqs = compile_capability_requirements(route)
    meoh = next(r for r in reqs.material if r.name == "methanol")
    honest = (meoh.quantity.knowledge is QuantityKnowledge.LOWER_BOUND_PLUS_UNKNOWN
              and _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN)
    real = QuantityDemand.__dict__["combine"].__func__

    def drop_none(cls, uses):
        kept = [u for u in uses if u is not None]
        return real(cls, kept if kept else list(uses))

    with _patch(QuantityDemand, "combine", classmethod(drop_none)):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M64", "mixed-unit demand loses its gate (F65)", "quantity.QuantityDemand.exact_by_unit")
def m64():
    """methanol 10 mL + 5 g (two unit domains, never converted) vs a 0.001 mL methanol bottle: the mL domain is
    provably short -> BLOCKED. Mutant: a multi-unit demand exposes NO domain to the allocator -> FIT."""
    route = _micro_route(extra_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="5",
                                          unit="g", phase=Phase.LIQUID),))
    profile = _clean_profile(material_inventory=(_bottle("methanol-thimble", _METHANOL, qty="0.001"),
                                                 _bottle("acetic-pure", _ACETIC)))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.BLOCKED
    bad_units = _src_mutant(QuantityDemand.exact_by_unit, (
        "return {unit: exact_fraction(value, f\"quantity in {unit!r}\") for unit, value in self.known}",
        "return {} if len(self.known) > 1 else "
        "{unit: exact_fraction(value, f\"quantity in {unit!r}\") for unit, value in self.known}"))
    with _patch(QuantityDemand, "exact_by_unit", bad_units):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M65", "one multi-component package spent in two species graphs", "assess._max_flow (per-species split)")
def m65():
    """One 5 mL saturated brine (NaCl + water components) cannot supply 5 mL of NaCl brine AND 5 mL of water: the
    package is ONE node -> F+ = 5 < 10 -> BLOCKED. Mutant: each species' graph spends the package independently."""
    brine = material_library.sodium_chloride_saturated_wash(quantity=StockQuantity.of("5", "mL"))
    reqs = (_mreq(name="sodium chloride", qty=(("mL", "5"),),
                  spec=MaterialSpecification(states=(_state(SaturationState.SATURATED),))),
            _mreq(name="water", qty=(("mL", "5"),)))
    profile = _profile(material_inventory=(brine,))
    honest = _mat(profile, *reqs) is CapabilityStatus.BLOCKED
    with _patch(assess_mod, "_max_flow", _per_species_flow):
        bad = _mat(profile, *reqs) is not CapabilityStatus.BLOCKED
    return honest, bad


def _conc_table(real):
    def projected(use):
        spec = real(use)
        if any(t in ("conc.", "concentrated") for t in spec.unresolved_terms):
            return _floor_spec("0.95")  # BUG: the retired global adjective table ("conc." == >= 95%)
        return spec
    return projected


@mutant("M66", "generic 'conc.' manufactures >= 95%", "requirements._project_specification")
def m66():
    """F67: 'conc.' has no species-free meaning (conc. HCl ~37%, conc. H2SO4 ~96%). Honest: the typed unresolved term
    keeps HCl UNKNOWN against BOTH a real 37% bottle and an impossible 96% one. Mutant (the retired adjective table):
    the real 37% HCl BLOCKS and the impossible 96% aqueous HCl FITs."""
    hcl = _mol("Cl")
    use = _use("hydrochloric acid", ProcedureMaterialRole.NEUTRALIZE, identity=hcl, qty="5", formulation="conc.",
               spec=MaterialSpecification(unresolved_terms=("conc.",)))
    route = _micro_route(extra_uses=(use,))
    p37 = _micro_profile(_bottle("hcl-37", hcl, "0.36", "0.38", phase=Phase.AQUEOUS_SOLUTION))
    p96 = _micro_profile(_bottle("hcl-96-impossible", hcl, "0.96", "0.97", phase=Phase.AQUEOUS_SOLUTION))
    honest = (_micro_assess(route, p37).material.status is CapabilityStatus.UNKNOWN
              and _micro_assess(route, p96).material.status is CapabilityStatus.UNKNOWN)
    with _patch(requirements_mod, "_project_specification", _conc_table(requirements_mod._project_specification)):
        bad = (_micro_assess(route, p37).material.status is CapabilityStatus.BLOCKED
               and _micro_assess(route, p96).material.status is CapabilityStatus.FIT)
    return honest, bad


def _state_from(trigger, claim):
    """A mutant `StockMaterial.spec_view` that INFERS a state claim the bench never declared (the Round-IV adjective
    table's move, one layer over): if ``trigger(stock, view)`` holds and the family is undeclared, add ``claim``."""
    real = StockMaterial.spec_view

    def spec_view(self, key):
        view = real(self, key)
        if view is not None and trigger(self, view) and not any(type(c.state) is type(claim.state) for c in view.states):
            return dc.replace(view, states=view.states + (claim,))
        return view

    return spec_view


def _spec_case(req, bottle, trigger, claim):
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    with _patch(StockMaterial, "spec_view", _state_from(trigger, claim)):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M67", "a ~20% number satisfies 'saturated'", "stock.StockMaterial.spec_view (state inferred from number)")
def m67():
    req = _mreq(name="sodium chloride", qty=(("mL", "5"),),
                spec=MaterialSpecification(states=(_state(SaturationState.SATURATED),)))
    bottle = _bottle("nacl-20pct", "sodium chloride", "0.2", "0.21", phase=Phase.AQUEOUS_SOLUTION, qty="250")
    return _spec_case(req, bottle, lambda s, v: v.interval[0] >= Fraction(1, 5),
                      StateClaim(SaturationState.SATURATED, EvidenceKind.USER_DECLARED))


@mutant("M68", "a hydrate satisfies ANHYDROUS via its assay", "stock.StockMaterial.spec_view (state inferred from assay)")
def m68():
    req = _mreq(name="magnesium sulfate", qty=(("g", "2"),),
                spec=MaterialSpecification(states=(_state(HydrationState.ANHYDROUS),)))
    heptahydrate = _bottle("mgso4-7h2o", "magnesium sulfate", "0.98", "1", phase=Phase.SOLID, qty="250", unit="g")
    return _spec_case(req, heptahydrate, lambda s, v: v.interval[0] >= Fraction(97, 100),
                      StateClaim(HydrationState.ANHYDROUS, EvidenceKind.USER_DECLARED))


@mutant("M69", "a dilute LIQUID satisfies NEAT via its phase", "stock.StockMaterial.spec_view (state inferred from phase)")
def m69():
    req = _mreq(identity=_ISOAMYL, qty=(("mL", "15"),), phase=Phase.LIQUID,
                spec=MaterialSpecification(states=(_state(DilutionState.NEAT),)))
    ten_pct_in_hexane = _bottle("isoamyl-10pct-hexane", _ISOAMYL, "0.09", "0.11", phase=Phase.LIQUID)
    return _spec_case(req, ten_pct_in_hexane, lambda s, v: s.phase is Phase.LIQUID,
                      StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED))


@mutant("M70", "an unknown-basis 5% is treated as w/w", "material_spec._compare_composition (basis)")
def m70():
    req = _mreq(name="sodium bicarbonate", qty=(("mL", "50"),),
                spec=MaterialSpecification(composition=_comp("0.045", "0.055", basis=ConcentrationBasis.UNKNOWN)))
    bottle = _bottle("nahco3-5pct-ww", "sodium bicarbonate", "0.048", "0.052", phase=Phase.AQUEOUS_SOLUTION)
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    real = spec_mod._compare_composition

    def as_mass_fraction(r, stock):
        if r.basis is ConcentrationBasis.UNKNOWN:
            r = dc.replace(r, basis=ConcentrationBasis.MASS_FRACTION)
        return real(r, stock)

    with _patch(spec_mod, "_compare_composition", as_mass_fraction):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M71", "ASSUMED requirement + ASSUMED stock certify FIT (F71)", "material_spec.CERTIFYING_*_EVIDENCE")
def m71():
    req = _mreq(name="sodium bicarbonate", qty=(("mL", "50"),),
                spec=MaterialSpecification(composition=_comp("0.04", "0.06", ev=EvidenceKind.ASSUMED)))
    bottle = _bottle("nahco3-assumed", "sodium bicarbonate", "0.045", "0.055", phase=Phase.AQUEOUS_SOLUTION,
                     kind="assumed")
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    with _patch(spec_mod, "CERTIFYING_REQUIREMENT_EVIDENCE",
                spec_mod.CERTIFYING_REQUIREMENT_EVIDENCE | {EvidenceKind.ASSUMED}), \
            _patch(spec_mod, "CERTIFYING_STOCK_EVIDENCE", spec_mod.CERTIFYING_STOCK_EVIDENCE | {EvidenceKind.ASSUMED}):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M72", "an unrecognized formulation word disappears (F69)", "requirements._project_specification (raw text)")
def m72():
    """A use whose raw formulation ('fuming') the author could NOT type projects as an UNRESOLVED term -> UNKNOWN.
    Mutant: the untyped raw word is dropped -> 'no constraint' -> a plain pure bottle FITs."""
    route = _micro_route(extra_uses=(_use("nitric acid", ProcedureMaterialRole.REACTANT, qty="5",
                                          formulation="fuming"),))
    profile = _micro_profile(_bottle("nitric-acid-bottle", "nitric acid"))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.UNKNOWN
    bad_proj = _src_mutant(requirements_mod._project_specification, (
        "if raw:\n        return MaterialSpecification(unresolved_terms=(raw,))",
        "if raw:\n        return _EMPTY_SPEC"))
    with _patch(requirements_mod, "_project_specification", bad_proj):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M73", "IntervalEvidence source/method/domain change doesn't move the material/profile digest (F70)",
        "contracts.canonical_payload (MaterialComponent.evidence)")
def m73():
    def profile_with(locator, domain):
        comp = MaterialComponent.evidenced("sodium chloride", "active",
                                           _ev("0.26", "0.27", kind="quoted", locator=locator, domain=domain))
        bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "brine", "brine", (comp,), Phase.AQUEOUS_SOLUTION, "fixture")
        return custom(profile_id="f70", material_inventory=(bottle,))

    a, b = profile_with("source A", "25 C"), profile_with("source B", "a different domain")
    honest = a.profile_digest != b.profile_digest and a.material_inventory[0].digest != b.material_inventory[0].digest
    with _patch(contracts_mod, "canonical_payload", _omit_field_encoder(MaterialComponent, "evidence")):
        bad = a.profile_digest == b.profile_digest
    return honest, bad


def _mislabelled_band(kind=EvidenceKind.DERIVED):
    return IntervalEvidence(kind, "0.045", "0.055", ConcentrationBasis.MASS_FRACTION, ("fixture: nominal 5%",),
                            DerivationKernel.ASSUMED_BAND_V1,
                            (TypedInput("nominal", "5", InputUnit.PERCENT, EvidenceKind.ASSUMED),
                             TypedInput("half_width", "0.5", InputUnit.PERCENT, EvidenceKind.ASSUMED)),
                            "decorative +-0.5% width")


@mutant("M74", "a kernel relabelled with an incompatible evidence kind still constructs (F63/F71)",
        "derived_evidence.IntervalEvidence.__post_init__ (kind check)")
def m74():
    """Honest: an ASSUMED_BAND_V1 record labelled DERIVED is REFUSED; the honestly-labelled ASSUMED bottle stays
    UNKNOWN against a sourced 4-6% requirement. Mutant: the kind check is gone -> the decorative band constructs as
    DERIVED and CERTIFIES a FIT."""
    req = _mreq(name="sodium bicarbonate", qty=(("mL", "50"),),
                spec=MaterialSpecification(composition=_comp("0.04", "0.06")))

    def bottle_with(ev):
        return StockMaterial(STOCK_MATERIAL_SCHEMA, "nahco3", "nahco3",
                             (MaterialComponent.evidenced("sodium bicarbonate", "active", ev),),
                             Phase.AQUEOUS_SOLUTION, "fixture", quantity=StockQuantity.of("500", "mL"))

    try:
        _mislabelled_band()
        refused = False
    except ValueError:
        refused = True
    honest = refused and _mat(_profile(material_inventory=(bottle_with(_mislabelled_band(EvidenceKind.ASSUMED)),)),
                              req) is CapabilityStatus.UNKNOWN
    bad_init = _src_mutant(IntervalEvidence.__post_init__, ("if self.kind is not expected_kind:", "if False:"))
    with _patch(IntervalEvidence, "__post_init__", bad_init):
        bad = _mat(_profile(material_inventory=(bottle_with(_mislabelled_band()),)), req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M75", "a g/100 mL figure is fed to the g/100 g kernel (F72)", "derived_evidence.KERNELS (unit whitelist)")
def m75():
    def per_volume_record():
        return IntervalEvidence.build(
            kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
            basis=ConcentrationBasis.MASS_FRACTION, inputs=_solubility_inputs("35.7", InputUnit.G_PER_100ML_SOLUTION),
            source_locators=(_PC_NACL,), domain_of_validity="per-VOLUME figure relabelled")

    try:
        per_volume_record()
        honest = False
    except ValueError:
        honest = True
    key = DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1
    spec = derived_mod.KERNELS[key]
    widened = dc.replace(spec, units=spec.units | {InputUnit.G_PER_100ML_SOLUTION})
    with _patch_item(derived_mod.KERNELS, key, widened):
        try:
            bad = per_volume_record().kind is EvidenceKind.DERIVED
        except ValueError:
            bad = False
    return honest, bad


@mutant("M76", "an ASSUMED stock interval is treated as sourced", "stock.StockMaterial.spec_view (evidence strength)")
def m76():
    req = _mreq(name="sodium bicarbonate", qty=(("mL", "50"),),
                spec=MaterialSpecification(composition=_comp("0.04", "0.06")))
    bottle = _bottle("nahco3-assumed", "sodium bicarbonate", "0.045", "0.055", phase=Phase.AQUEOUS_SOLUTION,
                     kind="assumed")
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_view = _src_mutant(StockMaterial.spec_view, (
        "kinds.append(EvidenceKind.UNKNOWN if c.evidence is None else c.evidence.kind)",
        "kinds.append(EvidenceKind.UNKNOWN if c.evidence is None else (EvidenceKind.SOURCE_QUOTED "
        "if c.evidence.kind is EvidenceKind.ASSUMED else c.evidence.kind))"))
    with _patch(StockMaterial, "spec_view", bad_view):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M77", "one package double-spent across structure-key and name-key requirements (F75)",
        "assess._material_axis (bottle node identity)")
def m77():
    """One 25 mL bottle whose components list acetic acid under BOTH its structure key and its label name; one
    structure-keyed and one name-keyed requirement each commensurable with it, 20 mL apiece. Honest: ONE package node
    -> F+ 25 < 40 -> BLOCKED. Mutant: the package node is split per requirement -> each spends the whole 25 mL -> FIT."""
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-two-keys", "acetic acid (two keys)",
        (MaterialComponent.evidenced(_ACETIC, "active", _ev("1", "1")),
         MaterialComponent.evidenced("acetic acid", "label", _ev("0", "1", kind="unknown"),
                                     states=(StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED),))),
        Phase.LIQUID, "fixture", quantity=StockQuantity.of("25", "mL"))
    reqs = (_mreq(identity=_ACETIC, role="structure-keyed draw"),
            _mreq(name="acetic acid", role="name-keyed draw",
                  spec=MaterialSpecification(states=(_state(DilutionState.NEAT),))))
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, *reqs) is CapabilityStatus.BLOCKED
    bad_axis = _src_mutant(assess_mod._material_axis, (
        '("r", ri), ("b", bi), total)', '("r", ri), ("b", bi, ri), total)', 2),
        ('pess.append((("b", bi), "T", amount[1]))',
         'pess.extend((("b", bi, rj), "T", amount[1]) for rj in range(len(demands)))'),
        ('opt.append((("b", bi), "T", amount[1]))',
         'opt.extend((("b", bi, rj), "T", amount[1]) for rj in range(len(demands)))'),
        ('opt.append((("b", bi), "T", total))',
         'opt.extend((("b", bi, rj), "T", total) for rj in range(len(demands)))'))
    with _patch(assess_mod, "_material_axis", bad_axis):
        bad = _mat(profile, *reqs) is CapabilityStatus.FIT
    return honest, bad


@mutant("M78", "assessed-benign unknown-phase condensed waste -> AQUEOUS_NEUTRAL (F76)",
        "waste.derive_waste (empty-GHS branch)")
def m78():
    """The real isopentyl water byproduct: empty GHS, fate UNKNOWN. Honest: benign SPECIES, untyped STREAM -> unresolved,
    never AQUEOUS_NEUTRAL. Mutant (the Round-IV F76 rule): empty GHS earns AQUEOUS_NEUTRAL."""
    route = _isopentyl_route()

    def mutated():
        return _src_mutant(waste_mod.derive_waste, (
            'unresolved.add(f"waste: {label} ({b.hazard_name}, empty GHS)',
            'categories.add(WasteCapability.AQUEOUS_NEUTRAL) or (f"waste: {label} ({b.hazard_name}, empty GHS)'))

    return _waste_flip(route, verify_handling(route), mutated, "empty GHS) -- benign species, untyped waste stream")


def _da_route() -> ExperimentRoute:
    """A real single-product micro-route (butadiene + ethylene -> cyclohexene: no co-product), both inputs typed."""
    butadiene, ethylene, cyclohexene = _mol("C=CC=C"), _mol("C=C"), _mol("C1=CCCCC1")
    op1 = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, locator="fixture",
                             material_uses=(_use("butadiene", ProcedureMaterialRole.SUBSTRATE, identity=butadiene,
                                                 qty="5", unit="g"),
                                            _use("ethylene", ProcedureMaterialRole.REACTANT, identity=ethylene,
                                                 qty="3", unit="g")))
    step = ExperimentStep(STEP_SCHEMA, cyclohexene, (butadiene, ethylene), (cyclohexene,), (),
                          ConditionEnvelope(procedure=_procedure((op1,))))
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


@mutant("M79", "excess/residual source material vanishes from waste (F77)", "waste.derive_waste (residual legs)")
def m79():
    """A single-product route has no co-product stream, so its ONLY waste obligations are the unreacted/excess
    residuals of its inputs. Honest: both residuals unresolved -> waste UNKNOWN. Mutant: residuals are dropped -> the
    waste question has nothing left -> NOT_APPLICABLE (a clean pass on leftovers nobody routed)."""
    route = _da_route()
    profile = _clean_profile(waste_handling=frozenset(WasteCapability))
    _c, _r, unresolved = waste_mod.derive_waste(route)
    honest = (sum("unreacted/excess" in u for u in unresolved) == 2
              and _micro_assess(route, profile).waste.status is CapabilityStatus.UNKNOWN)
    bad_derive = _src_mutant(waste_mod.derive_waste, (
        "elif use.role in _CONSUMED_ROLES:", "elif False:"),
        ("for molecule in tuple(step.reactants) + tuple(step.reagents):", "for molecule in ():"))
    with _patch(waste_mod, "derive_waste", bad_derive):
        bad = _micro_assess(route, profile).waste.status is CapabilityStatus.NOT_APPLICABLE
    return honest, bad


@mutant("M80", "the 0.9 wire shape changes while the 0.8 schema id stays (F74)", "service.COMPILATION_RESPONSE_SCHEMA")
def m80():
    """Honest: the bumped response id lets a REAL v0.8 (main@df1b38d) response load as LEGACY, readiness preserved.
    Mutant: the 0.9 shape keeps the 0.8 id (no bump) -> the loader can no longer tell the generations apart and the
    genuine v0.8 artifact is refused as a malformed 'current' payload."""
    payload = _v08("response_isopentyl_acetate.json")
    honest_resp = response_from_payload(payload)
    honest = honest_resp.is_legacy_v08 and svc.COMPILATION_RESPONSE_SCHEMA != payload["schema_version"]
    with _patch(svc, "COMPILATION_RESPONSE_SCHEMA", payload["schema_version"]):
        try:
            response_from_payload(_v08("response_isopentyl_acetate.json"))
            bad = False
        except ValueError:
            bad = True
    return honest, bad


@mutant("M81", "a real v0.8 response is interpreted as native (F81)", "service.CompilationResponse.is_legacy_v08")
def m81():
    """Honest: a real v0.8 routes-mode response loads as LEGACY (frozen v0.8 digest rule; its stored result_digest
    verifies). Mutant: the legacy dispatch is gone -> it is read under the current digest rule -> refused with a digest
    mismatch (the exact Round-IV F81 behaviour) or loaded as native."""
    honest = response_from_payload(_v08("response_isopentyl_acetate.json")).is_legacy_v08
    with _patch(CompilationResponse, "is_legacy_v08", property(lambda self: False)):
        try:
            resp = response_from_payload(_v08("response_isopentyl_acetate.json"))
            bad = not resp.is_legacy_v08
        except ValueError:
            bad = True
    return honest, bad


@mutant("M82", "ProcessBounds None changes meaning inside a CapabilityProfile (F78)",
        "declarations.process_dimension_state")
def m82():
    """The SAME all-None ProcessBounds: legacy law UNCONSTRAINED (unchanged, still true for legacy callers); capability
    law UNDECLARED -> UNKNOWN against a real 60-minute demand. Mutant: the capability layer reads None with the legacy
    meaning (as an operator NO_LIMIT) -> process FIT."""
    from smartchem.process_constraints import ProcessFitStatus, evaluate_process_requirements
    req = ProcessRequirements(workup_included=True, provenance="fixture", elapsed_minutes=Interval(0, 60, "min"))
    profile = _profile()
    legacy = evaluate_process_requirements((req,), profile.process_bounds).status is ProcessFitStatus.UNCONSTRAINED
    honest = legacy and assess_mod._process_axis((req,), profile).status is CapabilityStatus.UNKNOWN
    bad_state = _src_mutant(declarations_mod.process_dimension_state, (
        "return DimensionDeclaration.UNDECLARED", "return DimensionDeclaration.NO_LIMIT"))
    with _patch(declarations_mod, "process_dimension_state", bad_state):
        bad = assess_mod._process_axis((req,), profile).status is CapabilityStatus.FIT
    return honest, bad


# =================================================================================================================
# M83-M94 (Round V D13 / Lane G: every stated demand reaches its owning axis, or that axis fails closed)
# =================================================================================================================

@mutant("M83", "untyped op.materials / envelope catalyst / medium dropped (Lane G P0-1)",
        "requirements._untyped_source_materials")
def m83():
    route = _micro_route(materials=("sulfuric acid",), catalysts=("sulfuric acid",), medium="toluene")
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_untyped_source_materials", lambda r: []):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M84", "balanced species with no hazard record skipped (Lane G P0-2b)", "requirements._hazard_scan (balanced)")
def m84():
    """methyl acetate (a balanced product) has NO hazard record. Honest: hazard-unresolved -> containment UNKNOWN even
    under a hood. Mutant: the balanced-species leg is skipped -> containment FIT."""
    route = _micro_route()
    profile = _micro_profile(containment=frozenset({ContainmentCapability.FUME_HOOD}))
    honest = _micro_assess(route, profile).containment.status is CapabilityStatus.UNKNOWN
    bad_scan = _src_mutant(requirements_mod._hazard_scan, ("for molecule in (*step.reactants, *step.products):",
                                                          "for molecule in ():"))
    with _patch(requirements_mod, "_hazard_scan", bad_scan):
        bad = _micro_assess(route, profile).containment.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M85", "possession-only / unknown-fraction bottle as a G- source (Lane G P0-3)", "assess._edge (commensurable)")
def m85():
    lead = _bottle("lead-possession-only", "lead", "0", "1", phase=Phase.UNKNOWN, qty="500", unit="g", kind="none")
    req = _mreq(name="lead", qty=(("g", "10"),))
    profile = _profile(material_inventory=(lead,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, ("commensurable = status is CapabilityStatus.FIT and (",
                                              "commensurable = status is CapabilityStatus.FIT or ("))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


def _bench_process():
    return presets_mod._bench_process_bounds()


@mutant("M86", "an envelope duration outside the process record is unread (Lane G P0-4)",
        "requirements._process_unresolved")
def m86():
    process = ProcessRequirements(workup_included=True, provenance="fixture", elapsed_minutes=Interval(0, 60, "min"))
    route = _micro_route(duration=Interval(30240, 30240, "min"), process=process)  # a 3-week stated duration
    profile = _micro_profile(process_bounds=_bench_process())
    honest = _micro_assess(route, profile).process.status is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_process_unresolved", lambda r: ()):
        bad = _micro_assess(route, profile).process.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M87", "an apparatus-less hardware op reads NOT_APPLICABLE (Lane G P0-4)", "requirements._HARDWARE_OP_KINDS")
def m87():
    route = _micro_route(extra_ops=(_op(OperationKind.HEAT, OperationRole.REACTION),))
    honest = _micro_assess(route, _micro_profile()).equipment.status is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_HARDWARE_OP_KINDS", frozenset()):
        bad = _micro_assess(route, _micro_profile()).equipment.status is CapabilityStatus.NOT_APPLICABLE
    return honest, bad


@mutant("M88", "envelope T/P maximum collapsed to the process record (Lane G P0-4)",
        "requirements._physical_requirement (MAX over every source)")
def m88():
    process = ProcessRequirements(provenance="fixture", peak_temperature_k=416.15, min_pressure_atm=1.0,
                                  max_pressure_atm=1.0)
    route = _micro_route(temperature=Interval(600, 600, "K"), pressure=Interval(50, 50, "atm"), process=process)
    profile = _micro_profile(physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, max_pressure_atm=2.0,
                                                               min_pressure_atm=1.0))
    honest = _micro_assess(route, profile).physical.status is CapabilityStatus.BLOCKED
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        '_temperature(envelope.temperature, f"step {s_index} envelope")',
        'process is None and _temperature(envelope.temperature, f"step {s_index} envelope")'),
        ('_pressure(envelope.pressure, f"step {s_index} envelope")',
         'process is None and _pressure(envelope.pressure, f"step {s_index} envelope")'))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _micro_assess(route, profile).physical.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M89", "budget None -> pass (Lane G P2)", "assess._monetary_axis (UNDECLARED branch)")
def m89():
    req = _reqs(monetary=CostVector(cash=5.0, currency="USD", unit="USD"))
    a = assess(_profile(), req, _ps())
    honest = a.monetary.status is CapabilityStatus.UNKNOWN and a.overall is CapabilityStatus.UNKNOWN
    bad_axis = _src_mutant(assess_mod._monetary_axis, (
        'CapabilityStatus.UNKNOWN,\n            ("monetary: the declared profile states NO budget',
        'CapabilityStatus.UNCONSTRAINED,\n            ("monetary: the declared profile states NO budget'))
    with _patch(assess_mod, "_monetary_axis", bad_axis):
        m = assess(_profile(), req, _ps())
        bad = m.monetary.status is CapabilityStatus.UNCONSTRAINED and m.overall is CapabilityStatus.FIT
    return honest, bad


@mutant("M90", "the readiness tier the verdict was folded under is not recorded (Lane G P1-4)",
        "assess.assess (readiness binding)")
def m90():
    req = _reqs(containment=frozenset({ContainmentCapability.FUME_HOOD}))  # BLOCKED under both tiers
    profile = _profile()

    def pair():
        return assess(profile, req, _ps()), assess(profile, req, _readiness_at(CONDITIONS_SUPPORTED))

    a, b = pair()
    honest = a.overall is b.overall is CapabilityStatus.BLOCKED and a.digest != b.digest \
        and a.readiness_tier == PROCESS_SPECIFIED
    bad_assess = _src_mutant(assess_mod.assess, (
        "readiness_tier=route_readiness.tier,", 'readiness_tier="UNRECORDED",'),
        ("readiness_digest=route_readiness.digest,", 'readiness_digest="UNRECORDED",'))
    with _patch(assess_mod, "assess", bad_assess):
        ma, mb = bad_assess(profile, req, _ps()), bad_assess(profile, req, _readiness_at(CONDITIONS_SUPPORTED))
        bad = ma.digest == mb.digest
    return honest, bad


@mutant("M91", "a prose-only op temperature with no process peak is unread (D13)",
        "requirements._physical_requirement (prose-only leg)")
def m91():
    hold = _op(OperationKind.HOLD, OperationRole.REACTION, apparatus=("reflux condenser",),
               temperature=EvidenceField.present("reflux", "fixture"))
    route = _micro_route(extra_ops=(hold,))
    honest = _micro_assess(route, _micro_profile()).physical.status is CapabilityStatus.UNKNOWN
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        "if (field is not None and field.is_present and _interval_of(field) is None",
        "if (False and field is not None and field.is_present and _interval_of(field) is None"))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _micro_assess(route, _micro_profile()).physical.status is CapabilityStatus.UNCONSTRAINED
    return honest, bad


@mutant("M92", "a spent stream from an untyped materials= op is deleted (Lane E latent P0)",
        "waste.derive_waste (operation-derived spent streams)")
def m92():
    """An ADD/WASH op whose auxiliary lives ONLY in `materials=` ('brine', no typed use). Honest: the OPERATION yields
    an unresolved spent stream. Mutant: spent streams come only from typed uses -> the stream silently vanishes."""
    wash = _op(OperationKind.ADD, OperationRole.WASH, materials=("brine",))
    route = _micro_route(extra_ops=(wash,))
    marker = "op #2 ADD/WASH leaves a spent stream (brine)"
    honest = any(marker in u for u in waste_mod.derive_waste(route)[2])
    bad_derive = _src_mutant(waste_mod.derive_waste, (
        "if op.role in _SPENT_STREAM_OP_ROLES or op.kind in _SPENT_STREAM_OP_KINDS:", "if False:"))
    bad = not any(marker in u for u in bad_derive(route)[2]) and not any("brine" in u for u in bad_derive(route)[2])
    return honest, bad


@mutant("M93", "NO_LIMIT allowed on a capability/physical dimension (D10)", "profile.NO_LIMIT_ELIGIBLE")
def m93():
    def build(dim):
        return custom(profile_id="no-limit-probe", no_limit_dimensions=frozenset({dim}))

    refusals = []
    for dim in ("allowed_attention", "max_temperature_k"):
        try:
            build(dim)
            refusals.append(False)
        except ValueError as exc:
            refusals.append("not NO_LIMIT-eligible" in str(exc))
    honest = all(refusals)
    widened = profile_mod.NO_LIMIT_ELIGIBLE | declarations_mod.PROCESS_DIMENSIONS | declarations_mod.PHYSICAL_DIMENSIONS
    with _patch(profile_mod, "NO_LIMIT_ELIGIBLE", widened):
        try:
            bad = "allowed_attention" in build("allowed_attention").no_limit_dimensions
        except (ValueError, AttributeError):
            bad = False
    return honest, bad


@mutant("M94", "a legacy v0.8 request with an injected capability profile is accepted (F81/T1)",
        "service.request_from_payload + CompilationRequest.__post_init__ (legacy dispatch)")
def m94():
    """The real T1 tamper (a genuine v0.8 request + an injected 0.9.0a1 poor-man profile). Honest: REFUSED. Mutant:
    both legacy-dispatch layers (the loader's smuggle check AND the record's own legacy guard -- each alone is backed
    by the other, so the mutant must sever the whole dispatch) are disabled -> it loads as a legacy request carrying a
    bench."""
    t1 = _v08("tamper/T1_request_v08id_injected_capability.json")
    try:
        request_from_payload(t1)
        honest = False
    except ValueError:
        honest = True
    bad_loader = _src_mutant(svc.request_from_payload, ("if smuggled:", "if False:"))
    bad_init = _src_mutant(CompilationRequest.__post_init__, (
        'if self.capability_profile is not None or self.capability_profile_origin != "":', "if False:"))
    with _patch(CompilationRequest, "__post_init__", bad_init):
        try:
            req = bad_loader(_v08("tamper/T1_request_v08id_injected_capability.json"))
            bad = req.is_legacy_v08 and req.capability_profile is not None
        except ValueError:
            bad = False
    return honest, bad


# =================================================================================================================
# M95-M105 (Round V Wave-C: the fresh non-author hostile review's proven breaks, parent-integrated fixes)
# =================================================================================================================

@mutant("M95", "a bottle-scoped state certifies a trace species (Wave-C K1)", "stock.StockMaterial.spec_view (state scope)")
def m95():
    """A NEAT acetone bottle carrying a trace of acetic acid: the NEAT claim describes the ACETONE component only.
    Honest: the acetic-acid NEAT demand is UNDETERMINED -> UNKNOWN. Mutant: states are read bottle-wide -> the solvent's
    NEAT certifies the trace -> FIT."""
    acetone = _mol("CC(C)=O")
    neat = (StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED),)
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetone-neat-trace-acid", "acetone (trace acetic acid)",
        (MaterialComponent.evidenced(acetone, "solvent", _ev("0.99", "1"), states=neat),
         MaterialComponent.evidenced(_ACETIC, "impurity", _ev("0", "0.01"))),
        Phase.LIQUID, "fixture", quantity=StockQuantity.of("500", "mL"))
    req = _mreq(identity=_ACETIC, spec=MaterialSpecification(states=(_state(DilutionState.NEAT),)))
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_view = _src_mutant(StockMaterial.spec_view, (
        "for claim in c.states:", "for claim in (cc for comp in self.components for cc in comp.states):"))
    with _patch(StockMaterial, "spec_view", bad_view):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M96", "the G- purity rule ignores basis and evidence strength (Wave-C K2)", "assess._edge (pure conjuncts)")
def m96():
    """A bare `MaterialComponent.of_molecule(x, 1.0, 1.0)` (no evidence record = UNKNOWN strength, basis UNKNOWN) is not
    a PROVEN pure draw. Honest: possible source only -> UNKNOWN. Mutant: the pre-Wave-C rule (lower bound == 1 alone)."""
    bottle = _bottle("ethanol-bare-one", _ETHANOL, kind="none")
    profile = _profile(material_inventory=(bottle,))
    req = _mreq(identity=_ETHANOL)
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, (
        "and view.basis in (ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION)", "and True"),
        ("and view.interval_evidence in CERTIFYING_STOCK_EVIDENCE", "and True"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M97", "a MOLAR magnitude is capped to 1 (Wave-C K3)", "stock.StockMaterial.spec_view (fraction-only cap)")
def m97():
    """6 M NaOH must be expressible as 6 mol/L, never squeezed to '1'. Honest: the MOLAR component's view reads exactly
    [6, 6] on basis MOLAR. Mutant: the [0, 1] cap is applied to every basis -> the view reads [.., 1]."""
    naoh = StockMaterial(STOCK_MATERIAL_SCHEMA, "naoh-6m", "6 M NaOH",
                         (MaterialComponent(stock_mod.MATERIAL_COMPONENT_SCHEMA, "sodium hydroxide", "active", 6.0, 6.0,
                                            ConcentrationBasis.MOLAR),), Phase.AQUEOUS_SOLUTION, "fixture")
    view = naoh.spec_view("sodium hydroxide")
    honest = view.basis is ConcentrationBasis.MOLAR and view.interval == (Fraction(6), Fraction(6))
    bad_view = _src_mutant(StockMaterial.spec_view, ("if basis in _FRACTION_BASES:", "if True:"))
    with _patch(StockMaterial, "spec_view", bad_view):
        bad = naoh.spec_view("sodium hydroxide").interval[1] == 1
    return honest, bad


@mutant("M98", "a raw string naming a SECOND species hides behind a typed name (Wave-C K4)",
        "requirements._name_covers (exact-name coverage)")
def m98():
    route = _micro_route(materials=("methanol", "acetic acid", "benzene in methanol"))
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    import re as _re

    def whole_word(use_name, raw):
        name, text = requirements_mod._norm_text(use_name), requirements_mod._norm_text(raw)
        return bool(name) and (name == text or _re.search(r"(?<!\w)" + _re.escape(name) + r"(?!\w)", text) is not None)

    with _patch(requirements_mod, "_name_covers", whole_word):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M99", "one physical package declared twice (Wave-C K5)", "profile.CapabilityProfile.__post_init__ (dup check)")
def m99():
    bottle = _bottle("ethanol-10ml", _ETHANOL, qty="10")
    req = _mreq(identity=_ETHANOL)  # 20 mL from one 10 mL package
    try:
        _profile(material_inventory=(bottle, bottle))
        refused = False
    except ValueError:
        refused = True
    honest = refused and _mat(_profile(material_inventory=(bottle,)), req) is CapabilityStatus.BLOCKED
    bad_init = _src_mutant(CapabilityProfile.__post_init__, (
        "if len(set(ids)) != len(ids) or len(set(digests)) != len(digests):", "if False:"))
    with _patch(CapabilityProfile, "__post_init__", bad_init):
        try:
            bad = _mat(_profile(material_inventory=(bottle, bottle)), req) is CapabilityStatus.FIT
        except ValueError:
            bad = False
    return honest, bad


@mutant("M100", "non-ASCII digits parse as an exact quantity (Wave-C K6)", "material_spec.exact_fraction (grammar)")
def m100():
    arabic_indic_30 = "٣٠"
    try:
        StockQuantity.of(arabic_indic_30, "mL")
        honest = False
    except ValueError:
        honest = True
    bad_parse = _src_mutant(spec_mod.exact_fraction, ("[0-9]", "\\d", 4))
    with _patch(spec_mod, "exact_fraction", bad_parse):
        try:
            bad = StockQuantity.of(arabic_indic_30, "mL").exact() == 30
        except ValueError:
            bad = False
    return honest, bad


@mutant("M101", "an assessment whose overall is not the fold of its axes constructs (Wave-C2)",
        "assess.CapabilityAssessment.__post_init__ (fold check)")
def m101():
    real = assess(_profile(), _reqs(containment=frozenset({ContainmentCapability.FUME_HOOD})), _ps())
    assert real.overall is CapabilityStatus.BLOCKED
    try:
        dc.replace(real, overall=CapabilityStatus.FIT)
        honest = False
    except ValueError:
        honest = True
    bad_init = _src_mutant(assess_mod.CapabilityAssessment.__post_init__, ("if self.overall is not expected:",
                                                                          "if False:"))
    with _patch(assess_mod.CapabilityAssessment, "__post_init__", bad_init):
        try:
            bad = dc.replace(real, overall=CapabilityStatus.FIT).is_capability_fit
        except ValueError:
            bad = False
    return honest, bad


@mutant("M102", "a raw DERIVED input with no locator certifies (Wave-C2 A1)", "derived_evidence._SOURCED_INPUT_KINDS")
def m102():
    """Honest: a kernel input self-labelled DERIVED with no locator is refused. Mutant (the pre-fix rule: only
    SOURCE_QUOTED needs a locator): it constructs, feeds a CLAMPED record, and CERTIFIES a >= 99% floor."""
    def uncited_clamped():
        return IntervalEvidence.build(
            kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, basis=ConcentrationBasis.MASS_FRACTION,
            inputs=(TypedInput("floor", "99.9", InputUnit.PERCENT, EvidenceKind.DERIVED),),
            source_locators=("fixture: a record-level locator only",), domain_of_validity="uncited floor")

    req = _mreq(identity=_ETHANOL, spec=_floor_spec("0.99"))
    try:
        uncited_clamped()
        honest = False
    except ValueError:
        honest = True
    with _patch(derived_mod, "_SOURCED_INPUT_KINDS", frozenset({EvidenceKind.SOURCE_QUOTED})):
        try:
            ev = uncited_clamped()
            bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "ethanol-uncited", "ethanol",
                                   (MaterialComponent.evidenced(_ETHANOL, "active", ev),), Phase.LIQUID, "fixture",
                                   quantity=StockQuantity.of("500", "mL"))
            bad = _mat(_profile(material_inventory=(bottle,)), req) is CapabilityStatus.FIT
        except ValueError:
            bad = False
    return honest, bad


@mutant("M103", "COMPLEMENT inherits the parent's sourced kind (Wave-C2 C2-5)", "derived_evidence.KERNELS[COMPLEMENT_V1]")
def m103():
    """The water balance of a sourced 95-98% H2SO4 assay rests on a BINARY-mixture premise: ASSUMED. Honest: a sourced
    2-5% water requirement vs that complement stays UNKNOWN. Mutant: COMPLEMENT inherits SOURCE_QUOTED -> FIT."""
    parent = next(ev for key, ev in material_library.INTERVAL_EVIDENCE.items() if key.startswith("sulfuric-acid"))
    req = _mreq(name="water", qty=(("mL", "5"),), spec=MaterialSpecification(composition=_comp("0.02", "0.05")))

    def acid_with_water_balance():
        water = IntervalEvidence.build(kernel=DerivationKernel.COMPLEMENT_V1, basis=ConcentrationBasis.MASS_FRACTION,
                                       parent=parent, domain_of_validity="binary premise")
        return water.kind, StockMaterial(
            STOCK_MATERIAL_SCHEMA, "h2so4-with-water", "conc. H2SO4",
            (MaterialComponent.evidenced(_mol("OS(=O)(=O)O"), "active", parent),
             MaterialComponent.evidenced("water", "balance", water)),
            Phase.LIQUID, "fixture", quantity=StockQuantity.of("500", "mL"))

    kind, bottle = acid_with_water_balance()
    honest = kind is EvidenceKind.ASSUMED and _mat(_profile(material_inventory=(bottle,)), req) is CapabilityStatus.UNKNOWN
    key = DerivationKernel.COMPLEMENT_V1
    with _patch_item(derived_mod.KERNELS, key, dc.replace(derived_mod.KERNELS[key], output_kind=None)):
        kind2, bottle2 = acid_with_water_balance()
        bad = kind2 is EvidenceKind.SOURCE_QUOTED and \
            _mat(_profile(material_inventory=(bottle2,)), req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M104", "a CAPABILITY_FIT is admitted on an unsigned THIN wire (Wave-C2)",
        "service.CompilationResponse._check_assessment_bindings (thin FIT refusal)")
def m104():
    """No corpus route reaches FIT, so the attacker FORGES one: the real fit-bench response, one PROCESS_SPECIFIED
    dossier's assessment rewritten to an all-clear FIT that is fold-consistent and bound to the right profile, route and
    readiness (so every replay-free binding passes), serialized THIN (no replay to re-derive from). Honest: refused.
    Mutant: the thin-FIT refusal is removed -> the forged CAPABILITY_FIT loads."""
    resp = _fit_response()
    idx = next(i for i, d in enumerate(resp.ranked_route_dossiers)
               if d.capability_assessment is not None and d.readiness.tier == PROCESS_SPECIFIED)
    a = resp.ranked_route_dossiers[idx].capability_assessment
    clear = AxisResult(CapabilityStatus.FIT, ("forged: all clear",))
    forged = dc.replace(a, **{ax: clear for ax in ("material", "equipment", "physical", "process", "containment",
                                                   "ventilation", "measurement", "waste", "procurement",
                                                   "attention_care", "monetary")},
                        overall=CapabilityStatus.FIT, overall_reasons=("forged: FIT",))
    dossiers = list(resp.ranked_route_dossiers)
    dossiers[idx] = dc.replace(dossiers[idx], capability_assessment=forged)
    payload = response_to_payload(dc.replace(resp, ranked_route_dossiers=tuple(dossiers)), include_replay=False)
    try:
        response_from_payload(payload)
        honest = False
    except ValueError as exc:
        honest = "THIN_ADVISORY" in str(exc)
    bad_check = _src_mutant(CompilationResponse._check_assessment_bindings, (
        "if refuse_fit_on_thin and a.is_capability_fit:", "if False:"))
    with _patch(CompilationResponse, "_check_assessment_bindings", bad_check):
        try:
            loaded = response_from_payload(payload)
            bad = loaded.ranked_route_dossiers[idx].capability_assessment.is_capability_fit
        except ValueError:
            bad = False
    return honest, bad


@mutant("M105", "a non-stoichiometric use of a leaf's structure erases its consumption (Wave-C nag)",
        "requirements._STOICHIOMETRIC_ROLES")
def m105():
    """acetic acid appears only as a 5 mL WASH use while the balanced step CONSUMES it as a reactant. Honest: the leaf
    reactant keeps its own UNKNOWN-quantity demand -> material UNKNOWN. Mutant: any typed use of the structure
    suppresses the leaf -> the consumed charge disappears behind the wash -> FIT."""
    uses = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID),
            _use("acetic acid", ProcedureMaterialRole.WASH, identity=_ACETIC, qty="5", phase=Phase.LIQUID))
    route = _micro_route(base_uses=uses)
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_STOICHIOMETRIC_ROLES", frozenset(ProcedureMaterialRole)):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


# =================================================================================================================
# runner
# =================================================================================================================

def run() -> dict:
    results = []
    for mid, title, target, fn in _MUTANTS:
        try:
            honest, bad = fn()
            if honest and bad:
                status = "KILLED"
            elif not honest:
                status = "SURVIVED (honest code did not produce the expected verdict -- fixture/law drift)"
            else:
                status = "SURVIVED (the injected bad behaviour did not show -- a real gap)"
        except Exception as exc:  # noqa: BLE001 -- a harness error is a FAILED kill, reported, never a pass
            status = f"SURVIVED (harness error: {type(exc).__name__}: {exc})"
            if os.environ.get("SMARTCHEM_MUT_DEBUG"):
                traceback.print_exc()
        results.append((mid, title, target, status))
        print(f"  [{status.split(' ')[0]}] {mid} {title}  <{target}>"
              + ("" if status == "KILLED" else f"\n        -> {status}"), flush=True)
    killed = {mid for mid, _t, _g, s in results if s == "KILLED"}
    retired_rows = []
    for mid, title, mechanism, reason, replacement in _RETIRED:
        valid = all(r in killed for r in replacement)
        retired_rows.append((mid, title, mechanism, reason, replacement, valid))
    return {"active": results, "retired": retired_rows, "deferred": list(_DEFERRED)}


def main() -> int:
    ids = [m[0] for m in _MUTANTS]
    print(f"v0.9 capability compiler mutation gate (RC Round V, {len(ids)} ACTIVE registered, {len(_RETIRED)} RETIRED, "
          f"{len(_DEFERRED)} DEFERRED):", flush=True)
    assert len(ids) == len(set(ids)), "duplicate mutant id"
    out = run()
    active = out["active"]
    killed = sum(1 for *_x, s in active if s == "KILLED")
    survived = len(active) - killed
    print("\nRETIRED (mechanism deleted by Round V; bad behaviour killed by the named ACTIVE replacement):")
    void = 0
    for mid, title, mechanism, reason, replacement, valid in out["retired"]:
        void += 0 if valid else 1
        print(f"  [{'RETIRED' if valid else 'VOID-RETIREMENT'}] {mid} {title}\n        deleted: {mechanism}\n"
              f"        replaced by: {', '.join(replacement)} ({'all KILLED' if valid else 'NOT all killed'})\n"
              f"        reason: {reason}")
    print("\nDEFERRED / UNCALIBRATED:" + (" none" if not out["deferred"] else ""))
    for mid, title, reason in out["deferred"]:
        print(f"  [DEFERRED] {mid} {title}: {reason}")
    print(f"\nACTIVE {killed}/{len(active)} killed, {survived} survived | RETIRED {len(out['retired'])} "
          f"({void} void) | DEFERRED {len(out['deferred'])}")
    return 0 if survived == 0 and void == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
