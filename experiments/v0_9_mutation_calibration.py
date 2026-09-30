"""V0.9-MUTATION-01: the calibrated mutation gate for the capability compiler (RC Round V + X-high: M1-M175).

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

X-high (barrier D14-D20 + D24): the four Round-V survivors were FIXTURE faults, rebuilt against the law (M38 = the full
keyless public-hash attacker; M86 at law level on a clean fully-declared process pair; M94 with a current snapshot;
M104 as the 2-factor thin-FIT x tier-binding family, provably unkillable as a single guard) plus their single-binding
siblings (M38b, M94b, M104b); M106-M147 pin every continuation law. Where a newer independent law (D24) masks an
axis-level flip, the mutant is read at the layer its own law governs (never by weakening the newer law). Fixture
defaults are CERTIFYING (SOURCE_QUOTED requirement phase, USER_DECLARED bottle phase) and the process pair is fully
declared, so no mutant survives for a fixture reason.

X-high D28 (Wave C5 transport-ledger audit): M203-M211 pin one law leg each -- the stripped corpus envelope (D28.1),
the re-derived IR diagnostics (D28.2), the non-null receipt digests and result count (D28.3), the disclosed
unconstrained-DAG label (D28.4, read through the ledger test's docstring cross-check), exact keys on the service and IR
containers and exact serial-hold numbers (D28.5), and the ledger forgery sweep itself (D28.6: a relabel with no
refusing forgery is flagged).

X-high D29 (Wave C6 closure audit): M212-M217 pin one law leg each -- a replayed step bound to the algebra as STRUCTURES
(D29.1 C6-F8: a formula-bound check lets a byproduct isomer erase a sourced waste block) and to the reaction centre the
algebra assigns (D29.1 / Foreman N4), exact keys on the capability codec's nodes, identity-loss entries and structural
candidates (D29.2 C6-NEW-1), and the ledger sweep's own-law lock (D29.3 C6-test: a mislabelled check is flagged, not
merely "refused").  M190 now reads re-execution with D29.1 held out in both arms (D29.1 masks its forgery on every load).

Run:  .venv/bin/python experiments/v0_9_mutation_calibration.py
      (dev only: SMARTCHEM_MUT_ONLY=M38,M104 runs a subset -- retirements then read VOID; the gate is the full run)
"""
from __future__ import annotations

import __future__ as _future
import collections
import contextlib
import copy
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
import smartchem.legacy_v08 as legacy_mod  # 0.9.5 I2: the frozen v0.8 kernel's home (M108/M116 patch it HERE)
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
    PhaseClaim,
    SaturationState,
    StateClaim,
    Tolerance,
)
from smartchem.procedure_evidence import (
    EvidenceField,
    EvidenceFieldStatus,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements
from smartchem.service import (
    CompilationRequest,
    CompilationResponse,
    TransformGrammar,
    build_recompile_request,
    ranked_summary_from_payload,
    request_from_payload,
    request_to_payload,
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
    """Temporarily set ``obj.name = value`` (modules and classes), restoring EXACTLY on exit.

    0.9.5: the process enumeration cache is cleared on entry AND exit -- a patch changes behaviour without changing any
    cache key, so a stale honest entry could otherwise mask a mutant (or a mutant's entry leak into the next arm)."""
    from smartchem.verification import ENUMERATION_CACHE

    had = name in getattr(obj, "__dict__", {})
    old = obj.__dict__.get(name) if had else None
    ENUMERATION_CACHE.clear()
    setattr(obj, name, value)
    try:
        yield
    finally:
        ENUMERATION_CACHE.clear()
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


#: X-high D15: a CLEAN, fully-declared process PAIR. The process axis is now independently correct -- a step record
#: that is ``None``/empty/workup-less, or a bench that leaves any time/attention/agitation/check dimension undeclared,
#: is UNKNOWN -- so every fixture that means "the process axis is clean, isolate something else" must declare BOTH
#: sides fully (never a mutant surviving for a fixture reason).
_CLEAN_PROCESS_RECORD = ProcessRequirements(
    workup_included=True, provenance="fixture: a fully-declared whole-step record",
    elapsed_minutes=Interval(0, 60, "min"), active_minutes=Interval(0, 30, "min"),
    attention=Attention.PASSIVE, agitation=Agitation.NONE)
_CLEAN_PROCESS_BOUNDS = ProcessBounds.of(
    max_step_minutes=10080.0, max_total_minutes=20160.0, max_active_minutes=600.0,
    allowed_attention=tuple(Attention), min_check_interval_minutes=1.0, allowed_agitation=tuple(Agitation))


def _reqs(**over) -> RouteCapabilityRequirements:
    base = dict(
        route_digest="rd", material=(), equipment=frozenset(), equipment_unrecognized=(),
        physical=PhysicalBounds.unconstrained(), process=(_CLEAN_PROCESS_RECORD,), containment=frozenset(),
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
        process_bounds=_CLEAN_PROCESS_BOUNDS, containment=frozenset(), ventilation=frozenset(),
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
            states: "tuple[StateClaim, ...]" = (), extra: "tuple[MaterialComponent, ...]" = (),
            phase_ev: EvidenceKind = EvidenceKind.USER_DECLARED) -> StockMaterial:
    """A single-species StockMaterial keyed by structure (``key`` a Molecule) or declared name (``key`` a str), whose
    interval carries a REAL IntervalEvidence record (``kind='none'`` = no evidence record = UNKNOWN strength). State
    claims are COMPONENT-scoped (Wave-C K1): they describe THIS species in this bottle, never the bottle. The bottle
    PHASE is an evidence-graded claim (X-high D18): the bench's own declaration (USER_DECLARED) by default; an UNKNOWN
    phase carries UNKNOWN evidence (the StockMaterial invariant)."""
    if kind == "none":
        comp = (MaterialComponent.of_molecule(key, "active", float(lo), float(hi)) if not isinstance(key, str)
                else MaterialComponent.known(key, "active", float(lo), float(hi)))
        comp = dc.replace(comp, states=tuple(states))
    else:
        comp = MaterialComponent.evidenced(key, "active", _ev(lo, hi, kind=kind, basis=basis), states=tuple(states))
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, mid, mid, (comp,) + tuple(extra), phase, "fixture",
        quantity=None if qty is None else StockQuantity.of(qty, unit),
        phase_evidence=EvidenceKind.UNKNOWN if phase is Phase.UNKNOWN else phase_ev,
    )


def _phase(phase, ev: EvidenceKind = EvidenceKind.SOURCE_QUOTED) -> "PhaseClaim | None":
    """X-high D18: a requirement-side phase as an evidence-graded claim -- a bare ``Phase`` becomes a SOURCE_QUOTED
    claim by default (the fixture's source states it); a ``PhaseClaim`` passes through; ``None`` stays absent."""
    if phase is None or isinstance(phase, PhaseClaim):
        return phase
    return PhaseClaim(phase, ev)


def _mreq(*, identity=None, name=None, qty: "tuple[tuple[str, str], ...]" = (("mL", "20"),), unstated: int = 0,
          spec: MaterialSpecification = MaterialSpecification(), phase: "Phase | PhaseClaim | None" = None,
          role: str = "fixture") -> MaterialRequirement:
    return MaterialRequirement(identity=identity, phase=_phase(phase), quantity=QuantityDemand(tuple(qty), unstated),
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


def _procedure(ops, **over) -> ProcedureEvidence:
    """The micro procedure (every whole-procedure summary silent); ``over`` sets summary fields (re-validated)."""
    proc = ProcedureEvidence(reaction_scope="fixture micro-route", source=None, scale=_UNK, operations=tuple(ops),
                             quench=_UNK, workup_isolation=_UNK, separation=_UNK, wash=_UNK, drying=_UNK,
                             purification=_UNK, analytical_verification=_UNK)
    return dc.replace(proc, **over) if over else proc


def _use(name, role, *, identity=None, qty=None, unit="mL", phase=None, formulation=None, spec=None,
         phase_ev: EvidenceKind = EvidenceKind.SOURCE_QUOTED):
    return ProcedureMaterialUse(name=name, role=role, identity=identity, formulation=formulation,
                                phase=_phase(phase, phase_ev),
                                quantity=None if qty is None else StockQuantity.of(qty, unit),
                                evidence_source="fixture micro-route", specification=spec)


_MICRO_BASE_USES = (
    _use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID),
    _use("acetic acid", ProcedureMaterialRole.REACTANT, identity=_ACETIC, qty="10", phase=Phase.LIQUID),
)


def _micro_route(*, extra_uses=(), materials=(), extra_ops=(), base_uses=_MICRO_BASE_USES, procedure_over=None,
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
    envelope = ConditionEnvelope(procedure=_procedure(ops, **(procedure_over or {})), **envelope_kw)
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


_FIT_RESPONSE_CACHE: list = []


def _fit_response():
    """The real isopentyl-acetate compilation under the fit bench (deterministic, frozen; cached so the expensive
    search runs ONCE -- every mutant derives its forgery with ``dataclasses.replace`` copies, never by mutation).
    Callers invoke it OUTSIDE any patch context, so the cache can never hold a mutated compile."""
    if not _FIT_RESPONSE_CACHE:
        req = build_recompile_request(
            "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
            helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
        )
        _FIT_RESPONSE_CACHE.append(run_compilation(req))
    return _FIT_RESPONSE_CACHE[0]


def _dual_profile_runs(profile):
    req_none = build_recompile_request(_FAST_TARGET, max_depth=2)
    resp_none = run_compilation(req_none)
    req_prof = build_recompile_request(_FAST_TARGET, capability_profile=profile, max_depth=2)
    resp_prof = run_compilation(req_prof)
    return req_none, resp_none, req_prof, resp_prof


def _v08(name: str) -> dict:
    return json.loads((_V08 / name).read_text())


def _try_load(payload: dict, **kw):
    """``(response, None)`` if the PUBLIC decoder admits a deep copy of ``payload``, else ``(None, refusal text)``."""
    try:
        return response_from_payload(copy.deepcopy(payload), **kw), None
    except ValueError as exc:
        return None, str(exc)


_FAST_PROFILE_CACHE: list = []


def _fast_profile_response():
    """The fast methyl-acetate compilation under the fit bench (cached). It carries NO PROCESS_SPECIFIED dossier, so a
    THIN payload of it exercises the replay-free capability bindings without the 0.8 thin-PS law refusing first -- and
    without deleting a dossier (X-high D24.14 refuses a response that does not cover every IR candidate)."""
    if not _FAST_PROFILE_CACHE:
        resp = run_compilation(build_recompile_request(_FAST_TARGET, capability_profile=isopentyl_capability_fit_bench(),
                                                       max_depth=2))
        assert len(resp.ranked_route_dossiers) >= 2
        assert all(d.readiness.tier != PROCESS_SPECIFIED for d in resp.ranked_route_dossiers)
        _FAST_PROFILE_CACHE.append(resp)
    return _FAST_PROFILE_CACHE[0]


def _thin(resp, dossiers) -> dict:
    return response_to_payload(dc.replace(resp, ranked_route_dossiers=tuple(dossiers)), include_replay=False)


_AXES = ("material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
         "procurement", "attention_care", "monetary")


def _forge_fit(assessment, **over):
    """A fold-CONSISTENT all-clear CAPABILITY_FIT forgery of ``assessment`` (every axis FIT, overall FIT)."""
    clear = AxisResult(CapabilityStatus.FIT, ("forged: all clear",))
    return dc.replace(assessment, **{ax: clear for ax in _AXES}, overall=CapabilityStatus.FIT,
                      overall_reasons=("forged: FIT",), **over)


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
    bad_edge = _src_mutant(assess_mod._edge, (  # the absent-species exit (after D24.8's name-only UNKNOWN branch)
        "        return None\n    view = stock.spec_view(key)",
        "        return _Edge(CapabilityStatus.FIT, True, f\"{stock.material_id}: BUG absent=100%\")\n"
        "    view = stock.spec_view(key)"))
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
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=poor_man(),
                                                  capability_profile_origin="poor-man"))
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


@mutant("M26", "known (certified) phase mismatch still passes", "assess._edge (phase gate)")
def m26():
    """X-high D18 rebuild. The isopentyl wrong-phase bench now reads UNKNOWN (its requirement phase is an AUTHOR
    inference, which can refute nothing), so the gate is exercised where the law says it DECIDES: a SOURCE_QUOTED
    LIQUID methanol demand vs the bench's USER_DECLARED SOLID methanol bottle -> VIOLATES -> no G+ edge -> BLOCKED.
    Mutant: the phase gate is skipped -> the pure bottle is a proven draw -> the BLOCK vanishes."""
    route = _micro_route()
    profile = _clean_profile(material_inventory=(_bottle("methanol-solid", _METHANOL, phase=Phase.SOLID),
                                                 _bottle("acetic-pure", _ACETIC)))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.BLOCKED
    bad_edge = _src_mutant(assess_mod._edge, ("if requirement.phase is not None:", "if False:"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _micro_assess(route, profile).material.status is not CapabilityStatus.BLOCKED
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
        "service.CompilationResponse._check_capability_coherence (rebind re-derivation equality)")
def m38():
    """Rebuilt against the KEYLESS attacker (A-SURV / A-WIRE). The old fixture recomputed only the question pin, so the
    PUBLIC ``result_digest`` refused it and the rebind was never reached. Now the attacker strips the bench's declared
    stock, re-binds every carried assessment's ``profile_digest`` to the stripped snapshot, and re-serializes through
    the public codec -- every unkeyed digest/pin (question digest, result digest, admissible list...) is recomputed
    consistently, and the carried assessments are STALE (their material reasons still cite the stripped bottles).
    Honest: REFUSED by the rebind re-derivation alone. Mutant: that ONE equality is severed (the replay-free bindings
    stay live) -> the stale assessments load.

    X-high D27.4 re-derives the whole ranked tuple (assessments included) whenever EVERY dossier carries its replay, a
    second layer that would mask this leg; the leg is SOLE guard on a THIN-labelled payload that still carries some
    replays (D27.4 and the canonical D27.7 stand aside there) -- so the witness drops one dossier's replay and relabels
    the wire THIN_ADVISORY (public digest recomputed). The fast methyl-acetate answer carries no PROCESS_SPECIFIED
    dossier, so the thin-PS law does not refuse first."""
    resp = _fast_profile_response()
    profile = resp.request.capability_profile
    bottle_ids = {b.material_id for b in profile.material_inventory}
    stripped = dc.replace(profile, material_inventory=())
    dossiers = tuple(dc.replace(d, capability_assessment=dc.replace(d.capability_assessment,
                                                                    profile_digest=stripped.profile_digest))
                     for d in resp.ranked_route_dossiers)
    forged = dc.replace(resp, request=dc.replace(resp.request, capability_profile=stripped),
                        ranked_route_dossiers=dossiers)
    payload = response_to_payload(forged)
    payload["transport_mode"] = svc.TRANSPORT_THIN_ADVISORY
    del payload["ranked_route_dossiers"][-1]["replay_payload"]
    _public_digest(payload, forged)
    _loaded, err = _try_load(payload)
    honest = err is not None and "replayed evidence does not support" in err
    bad_cc = _src_mutant(CompilationResponse._check_capability_coherence, (
        "if r.capability_assessment != rederived:", "if False:"))
    with _patch(CompilationResponse, "_check_capability_coherence", bad_cc):
        loaded, _err = _try_load(payload)
    bad = (loaded is not None and not loaded.request.capability_profile.material_inventory
           and any(bid in " ".join(d.capability_assessment.material.reasons)
                   for d in loaded.ranked_route_dossiers for bid in bottle_ids))
    return honest, bad


@mutant("M38b", "an assessment under a DIFFERENT bench snapshot loads on a thin wire",
        "service.CompilationResponse._check_assessment_bindings (profile binding)")
def m38b():
    """The replay-free profile binding alone: THIN wire (no rebind possible), the request's bench snapshot changed (its
    equipment stripped), the carried assessments left under the ORIGINAL profile_digest. Honest: REFUSED by the profile
    binding. Mutant: the binding is severed -> assessments computed under another bench load."""
    resp = _fast_profile_response()
    other = dc.replace(resp.request.capability_profile, equipment=frozenset())
    payload = response_to_payload(dc.replace(resp, request=dc.replace(resp.request, capability_profile=other)),
                                  include_replay=False)
    _loaded, err = _try_load(payload)
    honest = err is not None and "profile_digest" in err
    bad_bind = _src_mutant(CompilationResponse._check_assessment_bindings, (
        "if a.profile_digest != profile.profile_digest:", "if False:"))
    with _patch(CompilationResponse, "_check_assessment_bindings", bad_bind):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and any(d.capability_assessment.profile_digest != other.profile_digest
                                     for d in loaded.ranked_route_dossiers)
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
    """methanol drawn three times: 55 + 10 + 25 = 90 mL whole-route demand vs ONE proven 80 mL methanol bottle. Honest:
    BLOCKED (even the optimistic allocation falls short). Mutant: the monoid fold keeps only the FIRST draw (55 mL) ->
    the provable shortfall disappears -> FIT. (Micro route since X-high D24.8: on the isopentyl route the NaHCO3 wash
    bottle legitimately lists water by NAME, so it is a possible water source and the shortfall is no longer provable
    there -- a correct, independent law, not a gap.)"""
    draws = tuple(_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty=q, phase=Phase.LIQUID)
                  for q in ("55", "10", "25"))
    route = _micro_route(base_uses=draws + (_MICRO_BASE_USES[1],))
    profile = _clean_profile(material_inventory=(_bottle("methanol-80ml", _METHANOL, qty="80"),
                                                 _bottle("acetic-pure", _ACETIC)))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.BLOCKED
    real = QuantityDemand.__dict__["combine"].__func__

    def first_wins(cls, uses):
        uses = list(uses)
        first = next((u for u in uses if u is not None), None)
        return real(cls, [first] if first is not None else uses)

    with _patch(QuantityDemand, "combine", classmethod(first_wins)):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.FIT
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
        "if spec is not None and not (raw and spec == _EMPTY_SPEC):\n        return spec",
        "if spec is not None and not (raw and spec == _EMPTY_SPEC):\n        return _EMPTY_SPEC"))
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
    # X-high D24.8: the name-only bottle can never CERTIFY the structure (F44), but it is not proof of absence either
    # -> UNKNOWN (was BLOCKED before D24.8); the mutant lets the weaker key certify -> FIT.
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN

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
        "key = (species_key, canonical_digest(spec), phase_key)", "key = species_key"))
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
    acetic_key = stock_mod.structure_key(_ACETIC)
    real = requirements_mod._material_requirements

    def identity_floor(r_):
        return tuple(dc.replace(r, specification=_floor_spec("0.98"))
                     if r.identity is not None and stock_mod.structure_key(r.identity) == acetic_key else r
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


#: step + total time DECLARED, active UNDECLARED; every non-time dimension declared (so only the active row can gap).
_TIME_BOUNDS = ProcessBounds.of(max_step_minutes=1000.0, max_total_minutes=1000.0,
                                allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                                allowed_agitation=tuple(Agitation))


@mutant("M61", "partial ProcessBounds launders an unmet ACTIVE-time demand", "assess._PROCESS_TIME_DIMENSIONS")
def m61():
    req = ProcessRequirements(workup_included=True, provenance="fixture", attention=Attention.PASSIVE,
                              agitation=Agitation.NONE,
                              elapsed_minutes=Interval(0, 60, "min"), active_minutes=Interval(0, 30, "min"))
    profile = _profile(process_bounds=_TIME_BOUNDS)
    honest = assess_mod._process_axis((req,), profile).status is CapabilityStatus.UNKNOWN
    table = assess_mod._PROCESS_TIME_DIMENSIONS
    assert table[-1][1] == "max_active_minutes"
    with _patch(assess_mod, "_PROCESS_TIME_DIMENSIONS", table[:-1]):
        bad = assess_mod._process_axis((req,), profile).status is CapabilityStatus.FIT
    return honest, bad


@mutant("M62", "attention/agitation undeclared on the bench still certifies (PORT onto D15)",
        "assess._process_declaration_gaps (successor of _PROCESS_FAILCLOSE_DIMENSIONS)")
def m62():
    """PORTED, not retired: Round IV's fail-close table became X-high D15's always-applied profile declaration gaps.
    A bench declaring every TIME dimension but no attention/agitation modes cannot certify a whole step. Honest:
    UNKNOWN (and overall UNKNOWN). Mutant: both non-time declaration checks are removed -> FIT (and overall FIT)."""
    req = ProcessRequirements(attention=Attention.PASSIVE, agitation=Agitation.NONE, workup_included=True,
                              provenance="fixture", elapsed_minutes=Interval(0, 60, "min"),
                              active_minutes=Interval(0, 30, "min"))
    bounds = ProcessBounds.of(max_step_minutes=1000.0, max_total_minutes=1000.0, max_active_minutes=600.0)
    profile = _clean_profile(process_bounds=bounds)
    honest = (assess_mod._process_axis((req,), profile).status is CapabilityStatus.UNKNOWN
              and assess(profile, _reqs(process=(req,)), _ps()).overall is CapabilityStatus.UNKNOWN)
    bad_gaps = _src_mutant(assess_mod._process_declaration_gaps, (
        "if bounds.allowed_attention is None:", "if False:"), ("if bounds.allowed_agitation is None:", "if False:"))
    with _patch(assess_mod, "_process_declaration_gaps", bad_gaps):
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
    keeps the demand UNKNOWN against BOTH a 37% bottle and a 96% one -- the compiler never learns what the adjective
    means. Mutant (the retired adjective table, '>= 95%'): the 37% bottle BLOCKS and the 96% one FITs. (X-high D25.1:
    the fixture uses sulfuric acid, whose name the offline resolver maps to its own structure, so the orthogonal
    unresolvable-name law cannot mask the adjective law; the law is species-agnostic.)"""
    acid = _mol("OS(=O)(=O)O")
    use = _use("sulfuric acid", ProcedureMaterialRole.CATALYST, identity=acid, qty="5", formulation="conc.",
               spec=MaterialSpecification(unresolved_terms=("conc.",)))
    route = _micro_route(extra_uses=(use,))
    p37 = _micro_profile(_bottle("acid-37", acid, "0.36", "0.38", phase=Phase.AQUEOUS_SOLUTION))
    p96 = _micro_profile(_bottle("acid-96", acid, "0.96", "0.97", phase=Phase.AQUEOUS_SOLUTION))
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


def _spec_verdict_case(req, bottle, key, trigger, claim):
    """The state-inference law read at the layer it governs -- the specification verdict over ``spec_view``. X-high
    D24.5 separately refuses to let a NEAT/ANHYDROUS word make a draw commensurable, which masks an axis-level FIT flip;
    the inference itself (a state the bench never declared) must still never CERTIFY the demand."""
    def verdict():
        return spec_mod.compare_specification(req.specification, bottle.spec_view(key))[0]

    honest = verdict() is spec_mod.SpecVerdict.UNDETERMINED
    with _patch(StockMaterial, "spec_view", _state_from(trigger, claim)):
        bad = verdict() is spec_mod.SpecVerdict.SATISFIES
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
    return _spec_verdict_case(req, heptahydrate, "magnesium sulfate", lambda s, v: v.interval[0] >= Fraction(97, 100),
                              StateClaim(HydrationState.ANHYDROUS, EvidenceKind.USER_DECLARED))


@mutant("M69", "a dilute LIQUID satisfies NEAT via its phase", "stock.StockMaterial.spec_view (state inferred from phase)")
def m69():
    req = _mreq(identity=_ISOAMYL, qty=(("mL", "15"),), phase=Phase.LIQUID,
                spec=MaterialSpecification(states=(_state(DilutionState.NEAT),)))
    ten_pct_in_hexane = _bottle("isoamyl-10pct-hexane", _ISOAMYL, "0.09", "0.11", phase=Phase.LIQUID)
    return _spec_verdict_case(req, ten_pct_in_hexane, _ISOAMYL, lambda s, v: s.phase is Phase.LIQUID,
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
    """One 25 mL bottle whose components list acetic acid under BOTH its structure key and its label name (each at a
    certified 50 %); a structure-keyed and a name-keyed 20 mL requirement, each commensurable with it through a
    SATISFIED composition (X-high D24.5: a state word alone no longer makes a draw commensurable). Honest: ONE package
    node -> F+ 25 < 40 -> BLOCKED. Mutant: the package node is split per requirement -> each spends the whole 25 mL ->
    FIT."""
    half = MaterialSpecification(composition=_comp("0.45", "0.55"))
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-two-keys", "acetic acid (two keys)",
        (MaterialComponent.evidenced(_ACETIC, "active", _ev("0.5", "0.5")),
         MaterialComponent.evidenced("acetic acid", "label", _ev("0.5", "0.5"))),
        Phase.LIQUID, "fixture", quantity=StockQuantity.of("25", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
    reqs = (_mreq(identity=_ACETIC, role="structure-keyed draw", spec=half),
            _mreq(name="acetic acid", role="name-keyed draw", spec=half))
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
    """The SAME ProcessBounds whose three TIME dimensions are None (non-time dimensions declared): the legacy law reads
    None as unconstrained and FITS (unchanged, still true for legacy callers); the capability law reads it as
    UNDECLARED -> UNKNOWN against a real 60-minute step. Mutant: the capability layer reads None with the legacy meaning
    (an operator NO_LIMIT) -> process FIT."""
    from smartchem.process_constraints import ProcessFitStatus, evaluate_process_requirements
    bounds = ProcessBounds.of(allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                              allowed_agitation=tuple(Agitation))
    profile = _profile(process_bounds=bounds)
    legacy = evaluate_process_requirements((_CLEAN_PROCESS_RECORD,), bounds).status is ProcessFitStatus.FITS
    honest = legacy and assess_mod._process_axis((_CLEAN_PROCESS_RECORD,), profile).status is CapabilityStatus.UNKNOWN
    bad_state = _src_mutant(declarations_mod.process_dimension_state, (
        "return DimensionDeclaration.UNDECLARED", "return DimensionDeclaration.NO_LIMIT"))
    with _patch(declarations_mod, "process_dimension_state", bad_state):
        bad = assess_mod._process_axis((_CLEAN_PROCESS_RECORD,), profile).status is CapabilityStatus.FIT
    return honest, bad


# =================================================================================================================
# M83-M94 (Round V D13 / Lane G: every stated demand reaches its owning axis, or that axis fails closed)
# =================================================================================================================

@mutant("M83", "untyped op.materials / envelope catalyst dropped (Lane G P0-1)",
        "requirements._untyped_source_materials")
def m83():
    route = _micro_route(materials=("sulfuric acid",), catalysts=("sulfuric acid",))
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


@mutant("M86", "a stated duration not covered by the typed timeline is unread (Lane G P0-4 / D15)",
        "requirements.RouteCapabilityRequirements.process_unresolved (the one 'uncovered time demand' field)")
def m86():
    """Rebuilt (A-SURV): the old fixture left attention/agitation undeclared on the ROUTE, so the delegate's own gaps
    kept the axis UNKNOWN for ANOTHER reason. Now the route record and the bench model EVERY process dimension (clean
    pair) and the only defect is the 3-week envelope duration the record's 60-min ceiling cannot cover. Honest:
    UNKNOWN or BLOCKED; the control (no stated duration) FITs. Mutant (law level -- survives helper renames): the
    compiled requirements lose their "stated time demand not covered" field -> FIT."""
    route = _micro_route(duration=Interval(30240, 30240, "min"), process=_CLEAN_PROCESS_RECORD)
    control = _micro_route(process=_CLEAN_PROCESS_RECORD)
    profile = _micro_profile(process_bounds=_CLEAN_PROCESS_BOUNDS)
    readiness = evaluate_route(route)
    reqs = compile_capability_requirements(route)
    honest = (assess(profile, reqs, readiness).process.status in (CapabilityStatus.UNKNOWN, CapabilityStatus.BLOCKED)
              and _micro_assess(control, profile).process.status is CapabilityStatus.FIT)
    bad = assess(profile, dc.replace(reqs, process_unresolved=()), readiness).process.status is CapabilityStatus.FIT
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
        "readiness_tier=route_readiness.tier,", "readiness_tier=PROCESS_SPECIFIED,"),
        ("readiness_digest=route_readiness.digest,", 'readiness_digest="UNRECORDED",'))
    with _patch(assess_mod, "assess", bad_assess):
        ma, mb = bad_assess(profile, req, _ps()), bad_assess(profile, req, _readiness_at(CONDITIONS_SUPPORTED))
        bad = ma.digest == mb.digest
    return honest, bad


@mutant("M91", "a prose op temperature is dropped instead of carried as unread (D13 / D14 i)",
        "requirements._physical_requirement (prose leg)")
def m91():
    hold = _op(OperationKind.HOLD, OperationRole.REACTION, apparatus=("reflux condenser",),
               temperature=EvidenceField.present("reflux", "fixture"))
    route = _micro_route(extra_ops=(hold,))
    honest = _micro_assess(route, _micro_profile()).physical.status is CapabilityStatus.UNKNOWN
    bad_phys = _src_mutant(requirements_mod._physical_requirement, ("if _is_prose(field):", "if False:"))
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
    # X-high F-6 keeps its OWN "introduces untyped material 'brine'" line (legitimate extra defence), so the bad check
    # is the operation-derived spent-stream obligation alone.
    bad = not any(marker in u for u in bad_derive(route)[2])
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


def _legacy_request_with_current_profile() -> "tuple[dict, dict]":
    """(genuine v0.8 request payload, the SAME payload + a CURRENT, VALID poor-man snapshot and origin) -- so the only
    thing that can refuse the tamper is the legacy-smuggling family, never the injected profile's own schema check
    (the historical T1 fixture injected a stale v1alpha1 snapshot; A-SURV)."""
    genuine = _v08("request_ethyl_acetate_smiles.json")
    current = request_to_payload(build_recompile_request("smiles:CCOC(C)=O", capability_profile=poor_man()))
    tamper = copy.deepcopy(genuine)
    tamper["capability_profile"] = current["capability_profile"]
    tamper["capability_profile_origin"] = "poor-man"
    return genuine, tamper


@mutant("M94", "a legacy v0.8 request with an injected capability profile is accepted (F81/T1)",
        "service.request_from_payload + CompilationRequest.__post_init__ (legacy dispatch family)")
def m94():
    """Rebuilt (A-SURV). Honest: REFUSED; each legacy guard ALONE still refuses (the loader's smuggle check, the
    record's own legacy invariant and -- since X-high D28.5 -- the released v0.8 exact key set back each other -- the law,
    not one if-statement); the historical stale-snapshot T1 stays refused. Mutant: ALL THREE layers severed -> the v0.8
    identity loads carrying a bench."""
    genuine, tamper = _legacy_request_with_current_profile()

    def refused(loader, payload):
        try:
            loader(copy.deepcopy(payload))
            return False
        except ValueError:
            return True

    bad_loader = _src_mutant(svc.request_from_payload, ("if smuggled:", "if False:"))
    bad_init = _src_mutant(CompilationRequest.__post_init__, (
        'if self.capability_profile is not None or self.capability_profile_origin != "":', "if False:"))
    loader_only = refused(bad_loader, tamper)
    with _patch(CompilationRequest, "__post_init__", bad_init):
        init_only = refused(request_from_payload, tamper)
        # X-high D28.5 added a THIRD layer: the released v0.8 request key set has no capability keys, so the exact-key
        # law alone refuses too (the smuggle check and the record invariant both severed)
        keys_only = refused(bad_loader, tamper)
    honest = (request_from_payload(copy.deepcopy(genuine)).is_legacy_v08 and refused(request_from_payload, tamper)
              and loader_only and init_only and keys_only
              and refused(request_from_payload, _v08("tamper/T1_request_v08id_injected_capability.json")))
    # the mutant severs ALL THREE layers (the key law installed BEFORE the loader copy snapshots the module globals)
    with _patch(svc, "_require_payload_keys", lambda *_a, **_k: None), \
            _patch(CompilationRequest, "__post_init__", bad_init):
        bare_loader = _src_mutant(svc.request_from_payload, ("if smuggled:", "if False:"))
        try:
            req = bare_loader(copy.deepcopy(tamper))
            bad = req.is_legacy_v08 and req.capability_profile is not None
        except ValueError:
            bad = False
    return honest, bad


@mutant("M94b", "0.9 content NESTED deep inside a legacy request is silently dropped (2-factor)",
        "service._v09_only_keys (any depth) x service._constraints_from_payload (exact key set)")
def m94b():
    """A current poor-man snapshot NESTED inside a genuine v0.8 request's ``constraints``. The law ("0.9 content never
    rides a 0.8 identity, at any depth") is held by TWO layers: the any-depth 0.9-only-key scan AND the constraints
    codec's exact key set. Honest: REFUSED, and each layer alone still refuses (mutual defence in depth). Mutant: both
    severed -> the request loads as legacy with the nested bench SILENTLY DROPPED."""
    genuine, _tamper = _legacy_request_with_current_profile()
    nested = copy.deepcopy(genuine)
    nested["constraints"]["capability_profile"] = request_to_payload(
        build_recompile_request("smiles:CCOC(C)=O", capability_profile=poor_man()))["capability_profile"]

    def load():
        try:
            return request_from_payload(copy.deepcopy(nested))
        except ValueError:
            return None

    scan_off = _patch(svc, "_v09_only_keys", lambda payload: [])
    codec_off = _patch(svc, "_constraints_from_payload", _src_mutant(svc._constraints_from_payload, (
        "if set(payload) != expected:", "if False:")))
    honest_refused = load() is None
    with scan_off:
        scan_only = load() is None
    with codec_off:
        codec_only = load() is None
    honest = honest_refused and scan_only and codec_only
    with _patch(svc, "_v09_only_keys", lambda payload: []), _patch(
            svc, "_constraints_from_payload",
            _src_mutant(svc._constraints_from_payload, ("if set(payload) != expected:", "if False:"))):
        req = load()
    bad = req is not None and req.is_legacy_v08 and req.capability_profile is None
    return honest, bad


# =================================================================================================================
# M95-M105 (Round V Wave-C: the fresh non-author hostile review's proven breaks, parent-integrated fixes)
# =================================================================================================================

@mutant("M95", "a bottle-scoped state certifies a trace species (Wave-C K1)", "stock.StockMaterial.spec_view (state scope)")
def m95():
    """An ANHYDROUS magnesium sulfate bottle carrying a TRACE of sodium sulfate: the ANHYDROUS claim describes the
    MgSO4 component only. Pinned at the layer K1 governs -- the specification verdict over ``spec_view``. Honest: the
    sodium-sulfate ANHYDROUS demand is UNDETERMINED. Mutant: states are read bottle-wide -> the drier's claim
    certifies the trace -> SATISFIES. (X-high D24.5 now ALSO refuses to let a NEAT/ANHYDROUS word make a draw
    commensurable and drops NEAT beside a certified diluent -- independent laws that mask an axis-level flip, so the
    K1 law is read where it lives, not through the allocation.)"""
    anhydrous = (StateClaim(HydrationState.ANHYDROUS, EvidenceKind.USER_DECLARED),)
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "mgso4-anhydrous-trace-na2so4", "anhydrous MgSO4 (trace Na2SO4)",
        (MaterialComponent.evidenced("magnesium sulfate", "drier", _ev("0.99", "1"), states=anhydrous),
         MaterialComponent.evidenced("sodium sulfate", "impurity", _ev("0", "0.01"))),
        Phase.SOLID, "fixture", quantity=StockQuantity.of("500", "g"), phase_evidence=EvidenceKind.USER_DECLARED)
    req = _mreq(name="sodium sulfate", qty=(("g", "2"),),
                spec=MaterialSpecification(states=(_state(HydrationState.ANHYDROUS),)))

    def verdict():
        return spec_mod.compare_specification(req.specification, bottle.spec_view("sodium sulfate"))[0]

    honest = verdict() is spec_mod.SpecVerdict.UNDETERMINED
    bad_view = _src_mutant(StockMaterial.spec_view, (
        "for claim in c.states:", "for claim in (cc for comp in self.components for cc in comp.states):"))
    with _patch(StockMaterial, "spec_view", bad_view):
        bad = verdict() is spec_mod.SpecVerdict.SATISFIES
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
        ("and view.interval_evidence in _PURE_WITNESS_EVIDENCE", "and True"))
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


@mutant("M104", "a CAPABILITY_FIT is admitted on an unsigned THIN wire (Wave-C2; 2-factor)",
        "service.CompilationResponse._check_assessment_bindings (thin-FIT refusal x readiness-tier binding)")
def m104():
    """PROVED unkillable as a SINGLE guard (A-SURV): FIT => tier PROCESS_SPECIFIED (the top rung) => the 0.8 thin-PS law
    refuses first. So the law is tested as the FAMILY that stands where no PS dossier exists (the methyl-acetate response
    -- no dossier is deleted, D24.14): a fold-consistent all-FIT assessment claiming readiness PROCESS_SPECIFIED on a
    sub-PS dossier, THIN wire. Honest: REFUSED; each single-factor cell ALSO refuses (thin-FIT guard alone -> tier
    binding refuses; tier binding alone -> thin-FIT guard refuses: mutual defence in depth). Mutant: BOTH severed -> a
    forged CAPABILITY_FIT loads on an unsigned thin wire."""
    resp = _fast_profile_response()
    dossiers = list(resp.ranked_route_dossiers)
    dossiers[0] = dc.replace(dossiers[0], capability_assessment=_forge_fit(
        dossiers[0].capability_assessment, readiness_tier=PROCESS_SPECIFIED, readiness_digest="forged-ps-readiness"))
    payload = _thin(resp, dossiers)
    thin_guard = ("if refuse_fit_on_thin and a.is_capability_fit:", "if False:")
    tier_bind = ("if a.readiness_tier != r.readiness.tier or a.readiness_digest != r.readiness.digest:", "if False:")
    cells = {}
    for label, edits in (("thin-only", (thin_guard,)), ("tier-only", (tier_bind,)), ("both", (thin_guard, tier_bind))):
        with _patch(CompilationResponse, "_check_assessment_bindings",
                    _src_mutant(CompilationResponse._check_assessment_bindings, *edits)):
            cells[label] = _try_load(payload)
    _l, honest_err = _try_load(payload)
    honest = honest_err is not None and cells["thin-only"][1] is not None and cells["tier-only"][1] is not None
    loaded = cells["both"][0]
    bad = loaded is not None and loaded.ranked_route_dossiers[0].capability_assessment.is_capability_fit
    return honest, bad


@mutant("M104b", "an assessment folded under a DIFFERENT readiness tier loads (thin)",
        "service.CompilationResponse._check_assessment_bindings (readiness-tier binding)")
def m104b():
    """The tier binding alone (no FIT involved): a sub-PS dossier's real (non-FIT) assessment relabelled as folded
    under PROCESS_SPECIFIED, thin wire. Honest: REFUSED. Mutant: the binding is severed -> it loads."""
    resp = _fast_profile_response()
    dossiers = list(resp.ranked_route_dossiers)
    assert not dossiers[0].capability_assessment.is_capability_fit
    dossiers[0] = dc.replace(dossiers[0], capability_assessment=dc.replace(
        dossiers[0].capability_assessment, readiness_tier=PROCESS_SPECIFIED, readiness_digest="forged-ps-readiness"))
    payload = _thin(resp, dossiers)
    _l, err = _try_load(payload)
    honest = err is not None and "readiness" in err
    bad_bind = _src_mutant(CompilationResponse._check_assessment_bindings, (
        "if a.readiness_tier != r.readiness.tier or a.readiness_digest != r.readiness.digest:", "if False:"))
    with _patch(CompilationResponse, "_check_assessment_bindings", bad_bind):
        loaded, _err = _try_load(payload)
    bad = (loaded is not None and loaded.ranked_route_dossiers[0].readiness.tier != PROCESS_SPECIFIED
           and loaded.ranked_route_dossiers[0].capability_assessment.readiness_tier == PROCESS_SPECIFIED)
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
# M106-M147 (Round V X-high continuation: barrier D14-D20 -- every new law, each on a world whose OTHER axes are
# clean or irrelevant to the axis read; honest = the law's verdict, bad = the violating verdict)
# =================================================================================================================

@mutant("M106", "an assessment of a DIFFERENT route loads (thin)",
        "service.CompilationResponse._check_assessment_bindings (route binding)")
def m106():
    resp = _fast_profile_response()
    dossiers = list(resp.ranked_route_dossiers)
    dossiers[0] = dc.replace(dossiers[0], capability_assessment=dc.replace(
        dossiers[0].capability_assessment, route_digest=dossiers[1].route_digest))
    payload = _thin(resp, dossiers)
    _l, err = _try_load(payload)
    honest = err is not None and "route_digest" in err
    bad_bind = _src_mutant(CompilationResponse._check_assessment_bindings, (
        "if a.route_digest != r.route_digest:", "if False:"))
    with _patch(CompilationResponse, "_check_assessment_bindings", bad_bind):
        loaded, _err = _try_load(payload)
    bad = (loaded is not None and loaded.ranked_route_dossiers[0].capability_assessment.route_digest
           != loaded.ranked_route_dossiers[0].route_digest)
    return honest, bad


@mutant("M107", "the capability QUESTION is not folded into result_digest (two benches share one result identity)",
        "service.CompilationResponse.result_digest (capability-question fold)")
def m107():
    """A zero-dossier (INVALID_INPUT) response: no assessment carries a profile digest, so only the question fold
    separates the RESULT IDENTITY of the poor-man answer from the research-lab one. Honest: the two identities differ,
    and the producer signature over the poor-man answer refuses the bench swap. Mutant: the fold is gone -> the two
    answers share one result identity.  (Since X-high D27.2 the SIGNATURE also binds the bench through the whole-body
    wire digest -- M189 -- so the identity law is witnessed directly, not through the HMAC.)"""
    key = b"m107-producer-key"
    resp = run_compilation(build_recompile_request("ethyl acetate", capability_profile="poor-man"))
    assert resp.outcome.value == "INVALID_INPUT" and not resp.ranked_route_dossiers
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=research_lab(),
                                                  capability_profile_origin="research-lab"))
    signed = response_to_payload(resp, signing_key=key)
    forged = response_to_payload(swapped)
    forged["producer_signature"] = signed["producer_signature"]
    _l, err = _try_load(forged, verification_key=key, require_signature=True,
                        expected_request_digest=resp.request.semantic_digest)
    honest = resp.result_digest != swapped.result_digest and err is not None and "signature" in err
    real = CompilationResponse.__dict__["result_digest"]
    unfolded = _src_mutant(real.fget, (
        '*((("capability-question", self.capability_question_digest),)\n'
        '              if self.capability_question_digest is not None else ()),', "*(),"))
    with _patch(CompilationResponse, "result_digest", unfolded):  # the re-compiled source keeps its @property
        bad = resp.result_digest == swapped.result_digest
    return honest, bad


@mutant("M108", "the frozen v0.8 omission set is WIDENED past the 0.9-added fields",
        "legacy_v08._V08_OMITTED_FIELDS (frozen v0.8 digest rule)")
def m108():
    """The frozen rule omits EXACTLY the fields 0.9 added (measured, not guessed). Honest: a real v0.8 (main@df1b38d)
    response loads as LEGACY and verifies. Mutant: one genuine v0.8 field (RankedRouteSummary.fit_status) joins the
    omission set -> the genuine artifact is no longer re-encoded byte-for-byte and is refused."""
    honest = response_from_payload(_v08("response_isopentyl_acetate.json")).is_legacy_v08
    widened = {k: dict(v) for k, v in legacy_mod._V08_OMITTED_FIELDS.items()}
    widened["smartchem.service.RankedRouteSummary"]["fit_status"] = None
    with _patch(legacy_mod, "_V08_OMITTED_FIELDS", widened):
        _l, err = _try_load(_v08("response_isopentyl_acetate.json"))
    return honest, err is not None


def _tfield(value) -> EvidenceField:
    return EvidenceField.present(value, "fixture")


def _phys(route, **bounds) -> CapabilityStatus:
    return _micro_assess(route, _micro_profile(physical_bounds=PhysicalBounds.of(**bounds))).physical.status


_COOL_77 = _op(OperationKind.COOL, apparatus=("ice bath",), temperature=_tfield(Interval(77, 77, "K")))


@mutant("M109", "the LOW-temperature demand is never projected (F-1 / D14)",
        "requirements._physical_requirement (min_temperature_k = min over typed lows)")
def m109():
    route = _micro_route(extra_ops=(_COOL_77,))
    honest = _phys(route, max_temperature_k=500.0, min_temperature_k=273.15) is CapabilityStatus.BLOCKED
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        "min_temperature_k=min(lows) if lows else None,", "min_temperature_k=None,"))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _phys(route, max_temperature_k=500.0, min_temperature_k=273.15) is not CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M110", "a real low-temperature demand against an UNDECLARED floor passes (D14 per-dimension)",
        "assess._PHYSICAL_DIMENSIONS (min temperature row)")
def m110():
    route = _micro_route(extra_ops=(_COOL_77,))
    honest = _phys(route, max_temperature_k=500.0) is CapabilityStatus.UNKNOWN
    table = tuple(row for row in assess_mod._PHYSICAL_DIMENSIONS if row[1] != "min_temperature_k")
    assert len(table) == len(assess_mod._PHYSICAL_DIMENSIONS) - 1
    with _patch(assess_mod, "_PHYSICAL_DIMENSIONS", table):
        bad = _phys(route, max_temperature_k=500.0) is CapabilityStatus.FIT
    return honest, bad


@mutant("M111", "a PROSE op temperature is 'covered' by an unrelated process peak (F-10)",
        "requirements._physical_requirement (prose leg: no inferred relation)")
def m111():
    furnace = _op(OperationKind.HEAT, apparatus=("hot plate",), temperature=_tfield("650 C tube furnace"))
    route = _micro_route(extra_ops=(furnace,), process=ProcessRequirements(provenance="fixture", peak_temperature_k=300.0))
    honest = _phys(route, max_temperature_k=500.0) is CapabilityStatus.UNKNOWN
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        "if _is_prose(field):", "if _is_prose(field) and not has_peak:"))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _phys(route, max_temperature_k=500.0) is CapabilityStatus.FIT
    return honest, bad


@mutant("M112", "a PROSE op pressure is 'covered' by an unrelated process pressure extremum (F-10)",
        "requirements._physical_requirement (prose leg: no inferred relation)")
def m112():
    autoclave = _op(OperationKind.MIX, pressure=_tfield("50 atm autoclave"))
    rec = ProcessRequirements(provenance="fixture", min_pressure_atm=1.0, max_pressure_atm=1.0)
    route = _micro_route(extra_ops=(autoclave,), process=rec)
    honest = _phys(route, min_pressure_atm=1.0, max_pressure_atm=2.0) is CapabilityStatus.UNKNOWN
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        "if _is_prose(field):",
        'if _is_prose(field) and not (label == "pressure" and process is not None '
        'and process.max_pressure_atm is not None):'))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _phys(route, min_pressure_atm=1.0, max_pressure_atm=2.0) is CapabilityStatus.FIT
    return honest, bad


_HIGH_UNREAD = ("if op.kind in _HIGH_THERMAL_KINDS and not has_peak:", "if False:")


@mutant("M113", "a heat op with NO stated temperature is masked by an unrelated lower op statement (P4)",
        "requirements._physical_requirement (D14 ii)")
def m113():
    typed = _op(OperationKind.HEAT, apparatus=("hot plate",), temperature=_tfield(Interval(298, 298, "K")))
    distill = _op(OperationKind.DISTILL, apparatus=("simple distillation apparatus",))  # D24.16: a NAMED still
    route = _micro_route(extra_ops=(typed, distill))
    honest = _phys(route, max_temperature_k=350.0, min_temperature_k=273.15) is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_physical_requirement", _src_mutant(requirements_mod._physical_requirement,
                                                                        _HIGH_UNREAD)):
        bad = _phys(route, max_temperature_k=350.0, min_temperature_k=273.15) is CapabilityStatus.FIT
    return honest, bad


@mutant("M114", "a heat op with NO stated temperature is masked by the envelope's lower statement (P5)",
        "requirements._physical_requirement (D14 ii)")
def m114():
    route = _micro_route(extra_ops=(_op(OperationKind.HEAT, apparatus=("hot plate",)),),
                         temperature=Interval(298, 298, "K"))
    honest = _phys(route, max_temperature_k=350.0, min_temperature_k=273.15) is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_physical_requirement", _src_mutant(requirements_mod._physical_requirement,
                                                                        _HIGH_UNREAD)):
        bad = _phys(route, max_temperature_k=350.0, min_temperature_k=273.15) is CapabilityStatus.FIT
    return honest, bad


@mutant("M115", "the route LOW is aggregated by MAX, not MIN (D14)", "requirements._physical_requirement (LOW = min)")
def m115():
    cool = _op(OperationKind.COOL, apparatus=("ice bath",), temperature=_tfield(Interval(273.15, 273.15, "K")))
    heat = _op(OperationKind.HEAT, apparatus=("hot plate",), temperature=_tfield(Interval(373.15, 373.15, "K")))
    route = _micro_route(extra_ops=(cool, heat))
    honest = _phys(route, max_temperature_k=400.0, min_temperature_k=300.0) is CapabilityStatus.BLOCKED
    bad_phys = _src_mutant(requirements_mod._physical_requirement, (
        "min_temperature_k=min(lows) if lows else None,", "min_temperature_k=max(lows) if lows else None,"))
    with _patch(requirements_mod, "_physical_requirement", bad_phys):
        bad = _phys(route, max_temperature_k=400.0, min_temperature_k=300.0) is CapabilityStatus.FIT
    return honest, bad


@mutant("M116", "the new temperature floor breaks real v0.8 identities (no frozen-rule omission, D14/D22)",
        "legacy_v08._V08_OMITTED_FIELDS['smartchem.constraints.PhysicalBounds']")
def m116():
    honest = response_from_payload(_v08("response_isopentyl_acetate.json")).is_legacy_v08
    table = {k: v for k, v in legacy_mod._V08_OMITTED_FIELDS.items() if k != "smartchem.constraints.PhysicalBounds"}
    with _patch(legacy_mod, "_V08_OMITTED_FIELDS", table):
        _l, err = _try_load(_v08("response_isopentyl_acetate.json"))
    return honest, err is not None


@mutant("M117", "a legacy physical-bounds-v1alpha1 box carries a temperature floor (D14)",
        "constraints.PhysicalBounds.__post_init__ (v1alpha1 floor guard)")
def m117():
    import smartchem.constraints as constraints_mod

    def legacy_with_floor():
        return PhysicalBounds(constraints_mod.PHYSICAL_BOUNDS_SCHEMA_V1, 400.0, None, None, 250.0)

    try:
        legacy_with_floor()
        honest = False
    except ValueError:
        honest = PhysicalBounds(constraints_mod.PHYSICAL_BOUNDS_SCHEMA_V1, 400.0).min_temperature_k is None
    bad_init = _src_mutant(PhysicalBounds.__post_init__, (
        "if self.schema_version == PHYSICAL_BOUNDS_SCHEMA_V1 and self.min_temperature_k is not None:", "if False:"))
    with _patch(PhysicalBounds, "__post_init__", bad_init):
        try:
            bad = legacy_with_floor().min_temperature_k == 250.0
        except ValueError:
            bad = False
    return honest, bad


@mutant("M118", "the ranking box silently drops a declared temperature floor (MP6)",
        "experiment.drafter.ConstraintBox.of_bounds (floor carried)")
def m118():
    import smartchem.experiment.drafter as drafter_mod
    route = _micro_route(temperature=Interval(250, 300, "K"))
    bounds = PhysicalBounds.of(min_temperature_k=280.0)
    honest = drafter_mod.fit_route(route, drafter_mod.ConstraintBox.of_bounds(bounds)).status \
        is drafter_mod.RouteFitStatus.EXCLUDED
    bad_of = _src_mutant(drafter_mod.ConstraintBox.of_bounds, (
        "min_temperature_k=bounds.min_temperature_k,", "min_temperature_k=None,"))
    with _patch(drafter_mod.ConstraintBox, "of_bounds", bad_of):
        bad = drafter_mod.fit_route(route, drafter_mod.ConstraintBox.of_bounds(bounds)).status \
            is not drafter_mod.RouteFitStatus.EXCLUDED
    return honest, bad


def _proc(route) -> CapabilityStatus:
    return _micro_assess(route, _micro_profile(process_bounds=_CLEAN_PROCESS_BOUNDS)).process.status


@mutant("M119", "a PRESENT prose op duration is ignored (F-2 / D15)", "requirements._step_timeline (prose leg)")
def m119():
    hold = _op(OperationKind.HOLD, apparatus=("reflux condenser",), duration=_tfield("3 weeks"))
    route = _micro_route(extra_ops=(hold,), process=_CLEAN_PROCESS_RECORD)
    honest = _proc(route) is CapabilityStatus.UNKNOWN
    bad_tl = _src_mutant(requirements_mod._step_timeline, (
        'unresolved.append(f"{where} {field.value!r} is stated in prose',
        '(lambda *_a: None)(f"{where} {field.value!r} is stated in prose'))
    with _patch(requirements_mod, "_step_timeline", bad_tl):
        bad = _proc(route) is CapabilityStatus.FIT
    return honest, bad


@mutant("M120", "ordered op durations collapse by MAX instead of adding (F-3 / D15)",
        "requirements._step_timeline (op floors add)")
def m120():
    """Three sequential 60-min HOLDs. Leg 1: a record ceiling of 90 min -> the 180-min floor CONTRADICTS it -> UNKNOWN
    (MAX: 60 <= 90 -> FIT). Leg 2 (F-3b): a 30-min record floor, no ceiling, a 120-min step bench -> the ordered floor
    PROVES 180 > 120 -> BLOCKED (MAX: 60 -> no proof)."""
    holds = tuple(_op(OperationKind.HOLD, apparatus=("reflux condenser",),
                      duration=_tfield(Interval(60, 60, "min"))) for _ in range(3))
    base = dict(workup_included=True, provenance="fixture", active_minutes=Interval(0, 30, "min"),
                attention=Attention.PASSIVE, agitation=Agitation.NONE)
    leg1 = _micro_route(extra_ops=holds, process=ProcessRequirements(elapsed_minutes=Interval(0, 90, "min"), **base))
    leg2 = _micro_route(extra_ops=holds, process=ProcessRequirements(min_elapsed_minutes=30.0, **base))
    bench120 = dc.replace(_CLEAN_PROCESS_BOUNDS, max_step_minutes=120.0)

    def legs():
        return (_proc(leg1),
                _micro_assess(leg2, _micro_profile(process_bounds=bench120)).process.status)

    h1, h2 = legs()
    honest = h1 is CapabilityStatus.UNKNOWN and h2 is CapabilityStatus.BLOCKED
    with _patch(requirements_mod, "_step_timeline", _src_mutant(requirements_mod._step_timeline, (
            "op_floor += interval.lo", "op_floor = max(op_floor, interval.lo)"))):
        b1, b2 = legs()
    return honest, b1 is CapabilityStatus.FIT and b2 is not CapabilityStatus.BLOCKED


@mutant("M121", "NO_LIMIT turns a workup-less record on a silent bench into FIT (F-8 / D15 family)",
        "assess._process_axis (coverage gate + declaration gaps + no UNCONSTRAINED pass)")
def m121():
    rec = ProcessRequirements(workup_included=False, provenance="fixture", elapsed_minutes=Interval(0, 60, "min"))
    profile = _profile(process_bounds=ProcessBounds.unconstrained(),
                       no_limit_dimensions=frozenset({"max_step_minutes", "max_total_minutes", "max_active_minutes"}))
    honest = assess_mod._process_axis((rec,), profile).status is CapabilityStatus.UNKNOWN
    bad_axis = _src_mutant(assess_mod._process_axis, (
        "if coverage or declaration or unresolved or fit.status is not ProcessFitStatus.FITS:",
        "if unresolved or fit.status not in (ProcessFitStatus.FITS, ProcessFitStatus.UNCONSTRAINED):"))
    with _patch(assess_mod, "_process_axis", bad_axis):
        bad = assess_mod._process_axis((rec,), profile).status is CapabilityStatus.FIT
    return honest, bad


@mutant("M122", "a silent route on a silent bench is 'outside the question' (UNCONSTRAINED passes the fold, F-8)",
        "assess._process_axis (never UNCONSTRAINED for >= 1 step)")
def m122():
    profile = _profile(process_bounds=ProcessBounds.unconstrained())
    honest = assess_mod._process_axis((None,), profile).status is CapabilityStatus.UNKNOWN
    bad_axis = _src_mutant(assess_mod._process_axis, (
        "    if coverage or declaration or unresolved or fit.status is not ProcessFitStatus.FITS:",
        "    if fit.status is ProcessFitStatus.UNCONSTRAINED and not any(\n"
        "            r is not None and r.is_declared for r in requirements):\n"
        "        return AxisResult(CapabilityStatus.UNCONSTRAINED, reasons)\n"
        "    if coverage or declaration or unresolved or fit.status is not ProcessFitStatus.FITS:"))
    with _patch(assess_mod, "_process_axis", bad_axis):
        bad = assess_mod._process_axis((None,), profile).status is CapabilityStatus.UNCONSTRAINED
    return honest, bad


def _equip(route, *caps) -> CapabilityStatus:
    return _micro_assess(route, _micro_profile(equipment=frozenset(caps))).equipment.status


@mutant("M123", "an ignored consumable discharges a hardware op (F-4)",
        "requirements._equipment_requirement (post-resolution per-op guard)")
def m123():
    route = _micro_route(extra_ops=(_op(OperationKind.DRY, apparatus=("watch glass",)),))
    honest = _equip(route) is CapabilityStatus.UNKNOWN
    bad_eq = _src_mutant(requirements_mod._equipment_requirement, ("if not recognized:", "if not op.apparatus:"))
    with _patch(requirements_mod, "_equipment_requirement", bad_eq):
        bad = _equip(route) is CapabilityStatus.NOT_APPLICABLE
    return honest, bad


@mutant("M124", "a thermometer discharges a DISTILL op (F-4b)", "requirements._KIND_ADMISSIBLE")
def m124():
    route = _micro_route(extra_ops=(_op(OperationKind.DISTILL, apparatus=("thermometer",)),))
    honest = _equip(route, EquipmentCapability.THERMOMETER) is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_KIND_ADMISSIBLE", {}):
        bad = _equip(route, EquipmentCapability.THERMOMETER) is CapabilityStatus.FIT
    return honest, bad


def _meas(route, *methods) -> CapabilityStatus:
    return _micro_assess(route, _micro_profile(measurement=frozenset(methods))).measurement.status


@mutant("M125", "a second VERIFY op naming no method is masked by the first op's balance (P5b)",
        "requirements._measurement_requirement (per-VERIFY-op guard)")
def m125():
    route = _micro_route(extra_ops=(_op(OperationKind.VERIFY, apparatus=("analytical balance",)),
                                    _op(OperationKind.VERIFY, materials=("ferric chloride",))))
    honest = _meas(route, MeasurementMethod.MASS) is CapabilityStatus.UNKNOWN
    bad_m = _src_mutant(requirements_mod._measurement_requirement, ("if not recognized and not unrecognized:",
                                                                     "if False:"))
    with _patch(requirements_mod, "_measurement_requirement", bad_m):
        bad = _meas(route, MeasurementMethod.MASS) is CapabilityStatus.FIT
    return honest, bad


_RATE_AGITATION = 'for label, field in (("rate", op.rate), ("agitation", op.agitation)):'


@mutant("M126", "a PRESENT addition rate is ignored (F-9 / D16)", "requirements._effective_process (rate leg)")
def m126():
    add = _op(OperationKind.ADD, rate=_tfield("dropwise over 3 hours via syringe pump"))
    route = _micro_route(extra_ops=(add,), process=_CLEAN_PROCESS_RECORD)
    honest = _proc(route) is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_effective_process", _src_mutant(requirements_mod._effective_process, (
            _RATE_AGITATION, 'for label, field in (("agitation", op.agitation),):'))):
        bad = _proc(route) is CapabilityStatus.FIT
    return honest, bad


@mutant("M127", "a PRESENT op agitation is ignored (F-9 / D16)", "requirements._effective_process (agitation leg)")
def m127():
    # an ADD op: a MIX op on the clean record (agitation NONE) would ALSO trip D24.4 -- a second, correct reason that
    # would keep the axis UNKNOWN under the mutant (a fixture fault, never a kill).
    stirred = _op(OperationKind.ADD, agitation=_tfield("vigorous overhead mechanical stirring"))
    route = _micro_route(extra_ops=(stirred,), process=_CLEAN_PROCESS_RECORD)
    honest = _proc(route) is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_effective_process", _src_mutant(requirements_mod._effective_process, (
            _RATE_AGITATION, 'for label, field in (("rate", op.rate),):'))):
        bad = _proc(route) is CapabilityStatus.FIT
    return honest, bad


@mutant("M128", "a PRESENT endpoint criterion is ignored (F-9 / D16)",
        "requirements._measurement_requirement (endpoint leg)")
def m128():
    route = _micro_route(extra_ops=(_op(OperationKind.VERIFY, apparatus=("analytical balance",)),
                                    _op(OperationKind.ADD, OperationRole.WASH, endpoint=_tfield("basic to litmus"))))
    honest = _meas(route, MeasurementMethod.MASS) is CapabilityStatus.UNKNOWN
    bad_m = _src_mutant(requirements_mod._measurement_requirement, (
        "if op.endpoint is not None and op.endpoint.is_present:", "if False:"))
    with _patch(requirements_mod, "_measurement_requirement", bad_m):
        bad = _meas(route, MeasurementMethod.MASS) is CapabilityStatus.FIT
    return honest, bad


@mutant("M129", "a stated amount with no typed home is dropped (op.quantity, D16 -> D24.1 canonical rendering)",
        "requirements._material_unresolved (op.quantity leg)")
def m129():
    route = _micro_route(extra_ops=(_op(OperationKind.ADD, quantity=_tfield("500 mL + 500 mL")),))
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    bad_mu = _src_mutant(requirements_mod._material_unresolved, (
        "if not _is_canonical(field, render_op_quantity(op)):", "if False:"))
    with _patch(requirements_mod, "_material_unresolved", bad_mu):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M130", "a demand-carrying field loses its owner silently (the D13 coverage theorem)",
        "capability.coverage.FIELD_COVERAGE / missing_coverage")
def m130():
    import smartchem.capability.coverage as coverage_mod
    honest = coverage_mod.missing_coverage() == ()
    table = {k: v for k, v in coverage_mod.FIELD_COVERAGE.items() if k != ("ProcedureOperation", "rate")}
    with _patch(coverage_mod, "FIELD_COVERAGE", table):
        bad = "UNCOVERED ProcedureOperation.rate" in coverage_mod.missing_coverage()
    return honest, bad


@mutant("M131", "an untyped material a QUENCH op introduces vanishes from waste (F-6 / D17)",
        "waste.derive_waste (untyped-material obligation)")
def m131():
    route = _micro_route(extra_ops=(_op(OperationKind.ADD, OperationRole.QUENCH, materials=("ice water",)),))
    honest = any("introduces untyped material 'ice water'" in u for u in waste_mod.derive_waste(route)[2])
    bad_derive = _src_mutant(waste_mod.derive_waste, ("for raw in op.materials:", "for raw in ():"))
    bad = not any("ice water" in u for u in bad_derive(route)[2])
    return honest, bad


@mutant("M132", "a net-consumed reactant relabelled CATALYST certifies as a catalyst (F-7 / D17)",
        "requirements._role_contradiction + waste.derive_waste (net_consumes cross-check)")
def m132():
    uses = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID),
            _use("acetic acid", ProcedureMaterialRole.CATALYST, identity=_ACETIC, qty="10", phase=Phase.LIQUID))
    route = _micro_route(base_uses=uses)

    def observe():
        _cats, reasons, unresolved = waste_mod.derive_waste(route)
        acetic = next(r for r in compile_capability_requirements(route).material if r.name == "acetic acid")
        return (any("catalyst residual 'acetic acid'" in r and "HAZARDOUS" in r for r in reasons),
                any("NET-CONSUMED" in u and "acetic acid" in u for u in unresolved),
                any("role contradiction" in t for t in acetic.specification.unresolved_terms))

    hazardous, waste_flag, req_flag = observe()
    honest = not hazardous and waste_flag and req_flag
    with _patch(waste_mod, "derive_waste", _src_mutant(waste_mod.derive_waste, ("if key in contradicted:", "if False:"))), \
            _patch(requirements_mod, "_role_contradiction", lambda use, step: None):
        m_hazardous, m_waste_flag, m_req_flag = observe()
    return honest, m_hazardous and not m_waste_flag and not m_req_flag


_ISOPENTYL_MEDIUM = "neat; acid-catalyzed (conc. H2SO4); reflux then fractional distillation"


@mutant("M133", "a condition sentence in envelope.medium becomes a species (Part IV)",
        "requirements._untyped_source_materials (medium is provenance only)")
def m133():
    """Part IV: the flagship record's medium SENTENCE is condition prose, never a species. (D24.3 adds a TEXT-FREE
    material note for an uncovered medium on a procedure step -- the axis is UNKNOWN for that open question -- but the
    sentence itself must never become a name-keyed requirement, a hazard entry or a waste stream.) Honest: no
    requirement is keyed by the sentence and no hazard/waste line quotes it. Mutant: the deleted Round-V branch is
    restored -> the sentence is a species again."""
    route = _micro_route(medium=_ISOPENTYL_MEDIUM)

    def species() -> bool:
        reqs = compile_capability_requirements(route)
        return (any(r.name == _ISOPENTYL_MEDIUM for r in reqs.material)
                or any(_ISOPENTYL_MEDIUM in line for line in reqs.hazard_unresolved + reqs.waste.unresolved))

    honest = not species()
    real = requirements_mod._untyped_source_materials

    def with_medium(r):  # the DELETED Round-V branch, restored
        return real(r) + [(s.envelope.medium.strip(), f"step {i} envelope medium")
                          for i, s in enumerate(r.steps, start=1) if (s.envelope.medium or "").strip()]

    with _patch(requirements_mod, "_untyped_source_materials", with_medium):
        bad = species()
    return honest, bad


@mutant("M134", "a material role with no waste reading silently produces nothing (D17 totality)",
        "waste._check_role_totality + waste._SPENT_STREAM_ROLES")
def m134():
    rinse = _op(OperationKind.ADD, material_uses=(_use("cold water", ProcedureMaterialRole.RINSE, qty="5"),))
    route = _micro_route(extra_ops=(rinse,))
    marker = "spent workup stream 'cold water'"
    orphaned = waste_mod._SPENT_STREAM_ROLES - {ProcedureMaterialRole.RINSE}
    with _patch(waste_mod, "_SPENT_STREAM_ROLES", orphaned):
        try:
            waste_mod._check_role_totality()
            guard = False
        except RuntimeError:
            guard = True
    honest = guard and any(marker in u for u in waste_mod.derive_waste(route)[2])
    with _patch(waste_mod, "_SPENT_STREAM_ROLES", orphaned), _patch(waste_mod, "_check_role_totality", lambda: None):
        waste_mod._check_role_totality()
        bad = not any("'cold water'" in u for u in waste_mod.derive_waste(route)[2])
    return honest, bad


_MEOAC, _AC2O = _mol("CC(=O)OC"), _mol("CC(=O)OC(C)=O")


def _two_step_route(step1_uses, step2_uses) -> ExperimentRoute:
    """AcOH + MeOH -> MeOAc + H2O, then MeOAc + AcOH -> Ac2O + MeOH (both conserving; step 2 consumes MORE acetic acid
    and REGENERATES methanol) -- a real two-step ExperimentRoute for the S1/S2 order laws."""
    def step(target, reactants, products, uses):
        op = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                                material_uses=tuple(uses), locator="fixture")
        return ExperimentStep(STEP_SCHEMA, target, reactants, products, (),
                              ConditionEnvelope(procedure=_procedure((op,))))
    return ExperimentRoute(ROUTE_SCHEMA, (step(_MEOAC, (_ACETIC, _METHANOL), (_MEOAC, _WATER), step1_uses),
                                          step(_AC2O, (_MEOAC, _ACETIC), (_AC2O, _METHANOL), step2_uses)))


_ACETIC_10 = _use("acetic acid", ProcedureMaterialRole.REACTANT, identity=_ACETIC, qty="10", phase=Phase.LIQUID)


@mutant("M135", "a later step's consumption hides behind an earlier step's typed use (S1)",
        "requirements._external_inputs / leaf charge PER STEP")
def m135():
    route = _two_step_route(_MICRO_BASE_USES, ())
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    real = requirements_mod._external_inputs

    def route_wide(r):  # the pre-S1 route-wide leaf dedupe: one charge per identity for the whole route
        seen, out = set(), []
        for s_index, m in real(r):
            key = requirements_mod._species_ident(m)
            if key not in seen:
                seen.add(key)
                out.append((s_index, m))
        return out

    with _patch(requirements_mod, "_external_inputs", route_wide):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M136", "a species produced only LATER counts as internal for an EARLIER step (S2)",
        "requirements._external_inputs (step order)")
def m136():
    route = _two_step_route((_ACETIC_10,), (_ACETIC_10,))
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN

    def order_blind(r):
        produced = {requirements_mod._species_ident(p) for st in r.steps for p in st.products}
        out = []
        for s_index, st in enumerate(r.steps, start=1):
            seen = set()
            for m in st.reactants:
                key = requirements_mod._species_ident(m)
                if key in produced or key in seen:
                    continue
                seen.add(key)
                out.append((s_index, m))
        return out

    with _patch(requirements_mod, "_external_inputs", order_blind):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


_AI_METHANOL = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID,
                     phase_ev=EvidenceKind.AUTHOR_INFERRED),
                _MICRO_BASE_USES[1])
_PHASE_BLIND = ("certified = (required.evidence in CERTIFYING_REQUIREMENT_EVIDENCE",
                "certified = True or (required.evidence in CERTIFYING_REQUIREMENT_EVIDENCE")


def _solid_methanol_profile():
    return _clean_profile(material_inventory=(_bottle("methanol-solid", _METHANOL, phase=Phase.SOLID),
                                              _bottle("acetic-pure", _ACETIC)))


@mutant("M137", "an AUTHOR-INFERRED requirement phase certifies FIT (Part III / D18)",
        "material_spec.compare_phase (certifying evidence)")
def m137():
    route = _micro_route(base_uses=_AI_METHANOL)
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "compare_phase", _src_mutant(spec_mod.compare_phase, _PHASE_BLIND)):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M138", "an AUTHOR-INFERRED requirement phase certifies BLOCKED (Part III / D18)",
        "material_spec.compare_phase (certifying evidence)")
def m138():
    route = _micro_route(base_uses=_AI_METHANOL)
    honest = _micro_assess(route, _solid_methanol_profile()).material.status is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "compare_phase", _src_mutant(spec_mod.compare_phase, _PHASE_BLIND)):
        bad = _micro_assess(route, _solid_methanol_profile()).material.status is CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M139", "a certified phase (SOURCE_QUOTED vs USER_DECLARED) never decides (D18 liveness)",
        "material_spec.compare_phase (decides when both sides certify)")
def m139():
    route = _micro_route()

    def pair():
        return (_micro_assess(route, _micro_profile()).material.status,
                _micro_assess(route, _solid_methanol_profile()).material.status)

    match, mismatch = pair()
    honest = match is CapabilityStatus.FIT and mismatch is CapabilityStatus.BLOCKED
    with _patch(assess_mod, "compare_phase", lambda required, stock: (spec_mod.SpecVerdict.UNDETERMINED, "BUG")):
        m_match, m_mismatch = pair()
    return honest, m_match is CapabilityStatus.UNKNOWN and m_mismatch is CapabilityStatus.UNKNOWN


@mutant("M140", "a stock phase with NO evidence certifies (D18)", "material_spec.CERTIFYING_STOCK_EVIDENCE (phase)")
def m140():
    route = _micro_route()
    profile = _clean_profile(material_inventory=(
        _bottle("methanol-ungraded-phase", _METHANOL, phase_ev=EvidenceKind.UNKNOWN), _bottle("acetic-pure", _ACETIC)))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.UNKNOWN
    with _patch(spec_mod, "CERTIFYING_STOCK_EVIDENCE", spec_mod.CERTIFYING_STOCK_EVIDENCE | {EvidenceKind.UNKNOWN}):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M141", "a CLAMPED [1, 1] (an assay reading above 100%) proves purity (F-5 / D18)",
        "assess._PURE_WITNESS_EVIDENCE (CLAMPED excluded)")
def m141():
    loc = "fixture: titration assay quoted as 100-101%"
    ev = IntervalEvidence.build(
        kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "100", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, loc),
                TypedInput("high", "101", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, loc)),
        source_locators=(loc,), domain_of_validity="an assay reading above 100%")
    assert ev.kind is EvidenceKind.CLAMPED and (ev.low, ev.high) == ("1", "1")
    bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "ethanol-clamped", "ethanol",
                           (MaterialComponent.evidenced(_ETHANOL, "active", ev),), Phase.LIQUID, "fixture",
                           quantity=StockQuantity.of("500", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, _mreq(identity=_ETHANOL)) is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "_PURE_WITNESS_EVIDENCE", spec_mod.CERTIFYING_STOCK_EVIDENCE):
        bad = _mat(profile, _mreq(identity=_ETHANOL)) is CapabilityStatus.FIT
    return honest, bad


@mutant("M142", "a V1 kernel's arithmetic drifts outside the shipped record region undetected (D19)",
        "derived_evidence.KERNEL_KNOWN_ANSWERS (region coverage)")
def m142():
    """The solubility kernel is edited to differ ONLY above s = 40 g/100 g: the shipped NaCl record (s = 36) still
    verifies -- the exact gap D19 closes. Honest: the frozen vectors (s = 60, 0..300) catch the drift at import time.
    Mutant: the vector set shrinks to the shipped-record region -> the drift passes silently."""
    key = DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1
    spec = derived_mod.KERNELS[key]

    def drifted(inputs, parent):
        if inputs["high"].exact <= 40:
            return spec.fn(inputs, parent)
        return Fraction(3, 5), Fraction(3, 5)

    def verifies() -> bool:
        try:
            derived_mod.verify_kernel_known_answers()
            return True
        except RuntimeError:
            return False

    with _patch_item(derived_mod.KERNELS, key, dc.replace(spec, fn=drifted)):
        nacl = next(ev for k, ev in material_library.INTERVAL_EVIDENCE.items() if k.startswith("sodium-chloride"))
        honest = not verifies() and nacl.verify()
        in_region = tuple(v for v in derived_mod.KERNEL_KNOWN_ANSWERS
                          if not (v.kernel is key and v.inputs and Fraction(v.inputs[-1][1]) > 40))
        with _patch(derived_mod, "KERNEL_KNOWN_ANSWERS", in_region):
            bad = verifies()
    return honest, bad


@mutant("M143", "a kernel's declared output kind changes without moving its semantic descriptor (D19)",
        "derived_evidence.kernel_semantic_descriptor (output kind)")
def m143():
    key = DerivationKernel.COMPLEMENT_V1
    spec = derived_mod.KERNELS[key]
    blind = _src_mutant(derived_mod.kernel_semantic_descriptor, (
        "spec.output_kind.value if spec.output_kind else None, ", ""))
    original, m_original = derived_mod.kernel_semantic_descriptor(key), blind(key)
    with _patch_item(derived_mod.KERNELS, key, dc.replace(spec, output_kind=None)):
        honest = derived_mod.kernel_semantic_descriptor(key) != original
        bad = blind(key) == m_original
    return honest, bad


@mutant("M144", "verified admission re-projects WITHOUT the request's profile (a false refusal, D20)",
        "service._check_verified_admission (capability profile)")
def m144():
    """A LIVENESS law: a profile request's genuinely-FITS dossier must pass ``require_verified_admission``. The fixture
    forces FITS routes with a synthetic process record on every searched envelope (a software control, context-managed).
    Honest: ADMITTED. Mutant (the pre-D20 re-projection without the profile): every assessed FITS dossier re-projects
    to a DIFFERENT summary -> REFUSED."""
    record = ProcessRequirements(elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
                                 agitation=Agitation.NONE, workup_included=True,
                                 provenance="synthetic software control (harness M144)")
    real = rt._conditions_for
    # the loads run under the SAME software-control corpus: since X-high D27.1 the loader re-derives every replayed
    # envelope from the corpus, so the synthetic record is the corpus's own for this control (outside it: refused D27.1)
    with _patch(rt, "_conditions_for", lambda target: dc.replace(real(target), process=record)):
        resp = run_compilation(build_recompile_request(_FAST_TARGET, max_depth=2, process=ProcessBounds.quick(),
                                                       capability_profile="poor-man"))
        assert any(d.fit_status == "FITS" for d in resp.ranked_route_dossiers), "fixture needs a FITS dossier"
        payload = response_to_payload(resp, include_replay=True)
        loaded, _err = _try_load(payload, require_verified_admission=True)
        honest = loaded is not None
        bad_va = _src_mutant(svc._check_verified_admission, (
            "capability_profile=response.request.capability_profile)", "capability_profile=None)"))
        with _patch(svc, "_check_verified_admission", bad_va):
            m_loaded, err = _try_load(payload, require_verified_admission=True)
    return honest, m_loaded is None and err is not None


@mutant("M145", "the consumer's capability-question pin is ignored (D20 (d))",
        "service.response_from_payload (expected_capability_question_digest)")
def m145():
    _req_none, _resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    payload = response_to_payload(resp_prof)
    other = build_recompile_request(_FAST_TARGET, capability_profile="research-lab",
                                    max_depth=2).capability_question_digest
    own, _e = _try_load(payload, expected_capability_question_digest=req_prof.capability_question_digest)
    _l, wrong = _try_load(payload, expected_capability_question_digest=other)
    _l, none = _try_load(payload, expected_capability_question_digest=None)
    honest = own is not None and wrong is not None and none is not None
    bad_rfp = _src_mutant(svc.response_from_payload, (
        "if (expected_capability_question_digest is not _NO_CAPABILITY_PIN",
        "if (False and expected_capability_question_digest is not _NO_CAPABILITY_PIN"))
    try:
        bad = bad_rfp(copy.deepcopy(payload), expected_capability_question_digest=other) is not None
    except ValueError:
        bad = False
    return honest, bad


@mutant("M146", "the display origin rides outside every digest (relabelled origin constructs, D20 (g))",
        "service.CompilationRequest.__post_init__ (origin law)")
def m146():
    req = build_recompile_request(_FAST_TARGET, capability_profile="poor-man", max_depth=2)
    try:
        dc.replace(req, capability_profile_origin="research-lab")
        honest = False
    except ValueError:
        honest = req.capability_profile_origin in ("", req.capability_profile.profile_id)
    bad_init = _src_mutant(CompilationRequest.__post_init__, (
        'elif self.capability_profile_origin not in ("", self.capability_profile.profile_id):', "elif False:"))
    with _patch(CompilationRequest, "__post_init__", bad_init):
        try:
            bad = dc.replace(req, capability_profile_origin="research-lab").capability_profile_origin == "research-lab"
        except ValueError:
            bad = False
    return honest, bad


@mutant("M147", "the thin-PS refusal is an EQUALITY, so a ladder extension opens the thin wire (D20 (3))",
        "service.CompilationResponse._check_readiness_coherence (tier_rank >= PS)")
def m147():
    """A LADDER-EXTENSION discriminator: a hypothetical rung above PROCESS_SPECIFIED ("PS_PLUS", ranked above it) is
    grafted onto the PS dossier's readiness (context-managed). Honest (``tier_rank >= PS``): the thin-PS law still
    refuses it. Mutant (the pre-D20 ``== PROCESS_SPECIFIED``): the higher rung slips through the thin law."""
    resp = _fit_response()
    real_tier = RouteReadiness.__dict__["tier"]
    real_rank = svc.tier_rank

    def bumped(self):
        tier = real_tier.fget(self)
        return "PS_PLUS" if tier == PROCESS_SPECIFIED else tier

    def rank(tier):
        return real_rank(PROCESS_SPECIFIED) + 1 if tier == "PS_PLUS" else real_rank(tier)

    bad_rc = _src_mutant(CompilationResponse._check_readiness_coherence, (
        "if refuse_process_specified_on_thin and tier_rank(r.readiness.tier) >= tier_rank(PROCESS_SPECIFIED):",
        "if refuse_process_specified_on_thin and r.readiness.tier == PROCESS_SPECIFIED:"))
    with _patch(RouteReadiness, "tier", property(bumped)), _patch(svc, "tier_rank", rank):
        try:
            resp._check_readiness_coherence(refuse_process_specified_on_thin=True)
            honest = False
        except ValueError as exc:
            honest = "THIN_ADVISORY" in str(exc)
        try:
            bad_rc(resp, refuse_process_specified_on_thin=True)
            bad = True
        except ValueError:
            bad = False
    return honest, bad


# =================================================================================================================
# M148-M175 (post-Wave-C' barrier amendment D24.1-D24.17: every D24 law, each read where its own law governs)
# =================================================================================================================

def _render(name: str):
    import smartchem.capability.coverage as coverage_mod
    return getattr(coverage_mod, name)


@mutant("M148", "prose op.quantity beside a QUANTIFIED typed use is trusted as display (D24.1 A1)",
        "requirements._material_unresolved (op.quantity canonical rendering)")
def m148():
    """The D16 'display trust' model trusted ``op.quantity`` whenever the op carried ANY quantified typed use -- so
    "5 L methanol" beside a typed 10 mL draw vanished. Honest (D24.1): the slot is display only when byte-equal to
    ``render_op_quantity(op)`` -> UNKNOWN; the canonical rendering itself stays display (control FIT). Mutant: the D16
    rule is restored -> FIT."""
    draw = _use("methanol", ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID)
    liar = _op(OperationKind.ADD, material_uses=(draw,), quantity=_tfield("5 L methanol"))
    canonical = dc.replace(liar, quantity=_tfield(_render("render_op_quantity")(liar)))
    route, control = _micro_route(extra_ops=(liar,)), _micro_route(extra_ops=(canonical,))
    honest = (_micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
              and _micro_assess(control, _micro_profile()).material.status is CapabilityStatus.FIT)
    bad_mu = _src_mutant(requirements_mod._material_unresolved, (
        "if not _is_canonical(field, render_op_quantity(op)):",
        "if not any(u.quantity is not None for u in op.material_uses):"))
    with _patch(requirements_mod, "_material_unresolved", bad_mu):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


_VERIFY_BALANCE = _op(OperationKind.VERIFY, apparatus=("analytical balance",))


@mutant("M149", "the analytical-verification text outruns the typed VERIFY methods (D24.1 A2)",
        "requirements._measurement_requirement (render_verification)")
def m149():
    def route(text):
        return _micro_route(extra_ops=(_VERIFY_BALANCE,),
                            procedure_over=dict(analytical_verification=_tfield(text)))

    lying, canonical = route("1H NMR and HPLC >= 99.5 %"), route("MASS")
    honest = (_meas(lying, MeasurementMethod.MASS) is CapabilityStatus.UNKNOWN
              and _meas(canonical, MeasurementMethod.MASS) is CapabilityStatus.FIT)
    bad_m = _src_mutant(requirements_mod._measurement_requirement, (
        "if verification.is_present and not _is_canonical(verification, render_verification(procedure)):",
        "if False:"))
    with _patch(requirements_mod, "_measurement_requirement", bad_m):
        bad = _meas(lying, MeasurementMethod.MASS) is CapabilityStatus.FIT
    return honest, bad


@mutant("M150", "a PRESENT whole-procedure summary reaches no axis (D24.1 A3)",
        "requirements._effective_process (render_summary)")
def m150():
    wash_op = _op(OperationKind.ADD, OperationRole.WASH)

    def route(text):
        return _micro_route(extra_ops=(wash_op,), process=_CLEAN_PROCESS_RECORD,
                            procedure_over=dict(wash=_tfield(text)))

    lying, canonical = route("vacuum distill at 1 mmHg, then dry in a vacuum oven at 390 K for 48 h"), \
        route("op 2 ADD/WASH")
    honest = _proc(lying) is CapabilityStatus.UNKNOWN and _proc(canonical) is CapabilityStatus.FIT
    bad_p = _src_mutant(requirements_mod._effective_process, (
        "if field.is_present and not _is_canonical(field, render_summary(procedure, name)):", "if False:"))
    with _patch(requirements_mod, "_effective_process", bad_p):
        bad = _proc(lying) is CapabilityStatus.FIT
    return honest, bad


@mutant("M151", "a PRESENT batch scale that is not the typed charge is trusted (D24.1)",
        "requirements._material_unresolved (render_scale)")
def m151():
    lying = _micro_route(procedure_over=dict(scale=_tfield("5 L methanol")))
    canonical = _micro_route(procedure_over=dict(scale=_tfield("10 mL methanol + 10 mL acetic acid")))
    honest = (_micro_assess(lying, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
              and _micro_assess(canonical, _micro_profile()).material.status is CapabilityStatus.FIT)
    bad_mu = _src_mutant(requirements_mod._material_unresolved, (
        "if procedure.scale.is_present and not _is_canonical(procedure.scale, render_scale(procedure)):",
        "if False:"))
    with _patch(requirements_mod, "_material_unresolved", bad_mu):
        bad = _micro_assess(lying, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M152", "a formulation word beside an EMPTY specification is dropped (D24.1 A9, F69 extended)",
        "requirements._project_specification (empty spec)")
def m152():
    route = _micro_route(extra_uses=(_use("nitric acid", ProcedureMaterialRole.REACTANT, qty="5",
                                          formulation="fuming", spec=MaterialSpecification()),))
    profile = _micro_profile(_bottle("nitric-acid-bottle", "nitric acid"))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.UNKNOWN
    bad_proj = _src_mutant(requirements_mod._project_specification, (
        "if spec is not None and not (raw and spec == _EMPTY_SPEC):", "if spec is not None:"))
    with _patch(requirements_mod, "_project_specification", bad_proj):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M153", "a vacuum op's sub-atmospheric demand is unread / contradicted by a 1 atm record (D24.1)",
        "requirements._physical_requirement (vacuum-op leg)")
def m153():
    """Leg A: a Buchner (VACUUM_FILTRATION) op with no typed pressure and no whole-step minimum -> UNKNOWN (mutant:
    UNCONSTRAINED, a pass). Leg B: the step record claims a whole-step minimum of 1 atm beside the vacuum op ->
    contradictory -> UNKNOWN (mutant: FIT against a 0.5-2 atm bench)."""
    vac = _op(OperationKind.FILTER, apparatus=("buchner funnel",))
    leg_a = _micro_route(extra_ops=(vac,))
    atm = ProcessRequirements(provenance="fixture", min_pressure_atm=1.0, max_pressure_atm=1.0)
    leg_b = _micro_route(extra_ops=(vac,), process=atm)

    def legs():
        return (_micro_assess(leg_a, _micro_profile()).physical.status,
                _phys(leg_b, min_pressure_atm=0.5, max_pressure_atm=2.0))

    ha, hb = legs()
    honest = ha is CapabilityStatus.UNKNOWN and hb is CapabilityStatus.UNKNOWN
    with _patch(requirements_mod, "_physical_requirement", _src_mutant(
            requirements_mod._physical_requirement, ("if record_min is None:", "if False:"),
            ("elif record_min >= 1:", "elif False:"))):
        ba, bb = legs()
    return honest, ba is CapabilityStatus.UNCONSTRAINED and bb is CapabilityStatus.FIT


@mutant("M154", "an EXPLICIT_NOT_APPLICABLE field carrying a value is accepted (D24.2 A4)",
        "procedure_evidence.EvidenceField.__post_init__ (N/A carries no value)")
def m154():
    """Honest: ``EvidenceField(N/A, value=650 K)`` is refused at construction. Mutant: accepted -- and since every
    capability reader gates on ``is_present``, the 650 K HEAT demand reaches NO axis: physical FIT against a 500 K
    bench (the step record's 300 K peak covers the 'untyped' heat op)."""
    def na_650():
        return EvidenceField(EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE, Interval(650, 650, "K"), "fixture",
                             "fixture: closed out")

    try:
        na_650()
        honest = False
    except ValueError:
        honest = True
    bad_init = _src_mutant(EvidenceField.__post_init__, (
        "if self.status is EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE and self.value is not None:", "if False:"))
    with _patch(EvidenceField, "__post_init__", bad_init):
        try:
            heat = _op(OperationKind.HEAT, apparatus=("hot plate",), temperature=na_650())
            route = _micro_route(extra_ops=(heat,), process=ProcessRequirements(provenance="fixture",
                                                                                 peak_temperature_k=300.0))
            bad = _phys(route, max_temperature_k=500.0) is CapabilityStatus.FIT
        except ValueError:
            bad = False
    return honest, bad


@mutant("M155", "an uncovered envelope.medium on a PROCEDURE step reaches no axis (D24.3 A5)",
        "requirements._material_unresolved (medium note)")
def m155():
    route = _micro_route(medium="benzene")
    honest = (_micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
              and not any(r.name == "benzene" for r in compile_capability_requirements(route).material))
    bad_mu = _src_mutant(requirements_mod._material_unresolved, (
        "if medium and not any(_name_covers(u.name, medium) for u in step_uses):", "if False:"))
    with _patch(requirements_mod, "_material_unresolved", bad_mu):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M156", "a MIX op on a step whose record declares agitation NONE certifies (D24.4 A6)",
        "requirements._effective_process (MIX leg)")
def m156():
    mix = _op(OperationKind.MIX)
    route = _micro_route(extra_ops=(mix,), process=_CLEAN_PROCESS_RECORD)
    stirred = _micro_route(extra_ops=(mix,), process=dc.replace(_CLEAN_PROCESS_RECORD, agitation=Agitation.MANUAL))
    honest = _proc(route) is CapabilityStatus.UNKNOWN and _proc(stirred) is CapabilityStatus.FIT
    bad_p = _src_mutant(requirements_mod._effective_process, ("if op.kind is OperationKind.MIX:", "if False:"))
    with _patch(requirements_mod, "_effective_process", bad_p):
        bad = _proc(route) is CapabilityStatus.FIT
    return honest, bad


@mutant("M157", "a component listed at [0, 0] supplies a demand (D24.5 B1-E)", "assess._species_key_in (upper 0)")
def m157():
    """A bottle LISTING ethanol at a certified [0, 0] vs an ethanol demand of 0-5 %: the phantom listing is ABSENT ->
    no G+ edge -> BLOCKED. Mutant: present-at-[0, 0] counts -> the 0-5 % composition is 'satisfied' -> FIT."""
    req = _mreq(identity=_ETHANOL, spec=MaterialSpecification(composition=_comp("0", "0.05")))
    profile = _profile(material_inventory=(_bottle("ethanol-phantom", _ETHANOL, "0", "0"),))
    honest = _mat(profile, req) is CapabilityStatus.BLOCKED
    bad_key = _src_mutant(assess_mod._species_key_in, ("if interval is None or interval[1] == 0:",
                                                        "if interval is None:"))
    with _patch(assess_mod, "_species_key_in", bad_key):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M158", "the whole-bottle contradiction (water [1, 1] + 0.3 g/mL NaCl) certifies a pure draw "
                "(D24.5 C1 x D25.2 -- 2-factor)",
        "stock.StockMaterial.__post_init__ (D25.2) x assess._others_absent (D24.5)")
def m158():
    """'water [1, 1]' beside a certified 0.3 g/mL NaCl is a CONTRADICTORY bottle, never a pure-water witness. Since
    D25.2 (Wave-C'' NEW-2) TWO layers pin the law, each the other's defence in depth -- so this is a 2-factor mutant
    (mutation tests the LAW, not each redundant guard): the bottle is REFUSED at construction, and a bottle smuggled past
    construction still fails the whole-bottle witness (UNKNOWN). Mutant: BOTH severed -> a proven pure draw -> FIT."""
    parts = (MaterialComponent.evidenced("water", "solvent", _ev("1", "1")),
             MaterialComponent.evidenced("sodium chloride", "solute",
                                         _ev("0.3", "0.3", basis=ConcentrationBasis.MASS_PER_VOLUME)))

    def build(components):
        return StockMaterial(STOCK_MATERIAL_SCHEMA, "water-with-salt", "water (with salt)", components,
                             Phase.AQUEOUS_SOLUTION, "fixture", quantity=StockQuantity.of("500", "mL"),
                             phase_evidence=EvidenceKind.USER_DECLARED)

    req = _mreq(name="water")
    try:
        build(parts)
        refused_at_construction = False
    except ValueError as exc:
        refused_at_construction = "D25.2" in str(exc)
    smuggled = build(parts[:1])
    object.__setattr__(smuggled, "components", parts)  # a bottle smuggled past __post_init__
    honest = refused_at_construction and _mat(_profile(material_inventory=(smuggled,)), req) is CapabilityStatus.UNKNOWN
    bad_init = _src_mutant(StockMaterial.__post_init__, ("if whole == 1 and any(", "if False and any("))
    bad_edge = _src_mutant(assess_mod._edge, ("and _others_absent(stock, view))", "and True)"))
    with _patch(StockMaterial, "__post_init__", bad_init), _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(_profile(material_inventory=(build(parts),)), req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M159", "a species-describing state (NEAT) carries the draw quantity (D24.5 B1)",
        "assess._edge (via_state = formulation-defining states only)")
def m159():
    """A 1 % acetic-acid bottle positively declared NEAT (the bench's word about the species) vs a NEAT 20 mL demand:
    the state is satisfied, but NEAT does not make 20 mL of the bottle 20 mL of acetic acid. Honest: UNKNOWN. Mutant:
    any satisfied state makes the draw commensurable -> FIT."""
    neat = (StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED),)
    profile = _profile(material_inventory=(_bottle("acetic-1pct-neat", _ACETIC, "0.01", "0.01", states=neat),))
    req = _mreq(identity=_ACETIC, spec=MaterialSpecification(states=(_state(DilutionState.NEAT),)))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, (
        "via_state = (satisfied and any(c.state in _FORMULATION_STATES for c in spec.states)",
        "via_state = (satisfied and bool(spec.states)"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


def _brine_demand():
    from smartchem.decompiler_conditions import _SPEC_SATURATED_AQUEOUS_NACL
    return _mreq(name="sodium chloride", qty=(("mL", "5"),), spec=_SPEC_SATURATED_AQUEOUS_NACL,
                 phase=PhaseClaim(Phase.AQUEOUS_SOLUTION, EvidenceKind.SOURCE_QUOTED))


@mutant("M160", "a formulation state over a certified lower bound of 0 carries the draw (D24.5 B1)",
        "assess._edge (via_state needs a certified positive fraction)")
def m160():
    """The LIVE corpus brine spec (SATURATED + SOLUTION, SOURCE_QUOTED) vs a bottle declared saturated brine whose NaCl
    component is certified only at [0, 0.27]: 'saturated' over a possibly-empty component proves no draw. Honest:
    UNKNOWN. Mutant: the positive-fraction conjunct is dropped -> FIT."""
    states = (StateClaim(SaturationState.SATURATED, EvidenceKind.USER_DECLARED),
              StateClaim(DilutionState.SOLUTION, EvidenceKind.USER_DECLARED))
    bottle = _bottle("brine-maybe-empty", "sodium chloride", "0", "0.27", phase=Phase.AQUEOUS_SOLUTION, states=states)
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, _brine_demand()) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, ("and view is not None and view.interval[0] > 0",
                                              "and view is not None"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, _brine_demand()) is CapabilityStatus.FIT
    return honest, bad


@mutant("M161", "a satisfied formulation-defining state never carries the draw (D24.5 liveness, corpus brine)",
        "assess._edge (via_state)")
def m161():
    """LIVENESS: the live corpus brine spec vs the library's saturated brine (certified NaCl fraction > 0, SATURATED +
    SOLUTION declared) is a PROVEN draw. Honest: FIT. Mutant: state commensurability disabled -> UNKNOWN."""
    brine = material_library.sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL"))
    profile = _profile(material_inventory=(brine,))
    honest = _mat(profile, _brine_demand()) is CapabilityStatus.FIT
    bad_edge = _src_mutant(assess_mod._edge, ("via_state = (satisfied and", "via_state = (False and"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, _brine_demand()) is CapabilityStatus.UNKNOWN
    return honest, bad


@mutant("M162", "a NEAT claim survives a certified positive diluent in the same bottle (D24.5 C2)",
        "stock.StockMaterial.spec_view (NEAT-vs-diluent drop)")
def m162():
    neat = (StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED),)
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-half-water", "acetic acid (50 % water, 'neat')",
        (MaterialComponent.evidenced(_ACETIC, "active", _ev("0.5", "0.5"), states=neat),
         MaterialComponent.evidenced("water", "diluent", _ev("0.5", "0.5"))),
        Phase.LIQUID, "fixture", quantity=StockQuantity.of("500", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
    spec = MaterialSpecification(states=(_state(DilutionState.NEAT),))

    def verdict():
        return spec_mod.compare_specification(spec, bottle.spec_view(_ACETIC))[0]

    honest = verdict() is spec_mod.SpecVerdict.UNDETERMINED
    with _patch(StockMaterial, "spec_view", _src_mutant(StockMaterial.spec_view, ("if diluted:", "if False:"))):
        bad = verdict() is spec_mod.SpecVerdict.SATISFIES
    return honest, bad


@mutant("M163", "an earlier step's BYPRODUCT feeds a later step for free (D24.6 B2)",
        "requirements._external_inputs (only the carried target is internal)")
def m163():
    """AcOH + MeOH -> MeOAc + H2O, then MeOAc + H2O -> AcOH + MeOH: step 2's water is step 1's BYPRODUCT (removed in
    its workup), not the carried target -- a real external demand. Honest: water is a leaf requirement and material is
    not FIT. Mutant (the pre-D24.6 rule: any earlier product is internal) -> the water demand vanishes -> FIT."""
    def step(target, reactants, products, uses):
        op = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                                material_uses=tuple(uses), locator="fixture")
        return ExperimentStep(STEP_SCHEMA, target, reactants, products, (),
                              ConditionEnvelope(procedure=_procedure((op,))))

    route = ExperimentRoute(ROUTE_SCHEMA, (
        step(_MEOAC, (_ACETIC, _METHANOL), (_MEOAC, _WATER), _MICRO_BASE_USES),
        step(_ACETIC, (_MEOAC, _WATER), (_ACETIC, _METHANOL), ())))
    water_key = requirements_mod._species_ident(_WATER)
    water_leaf = any(r.identity is not None and requirements_mod._species_ident(r.identity) == water_key
                     for r in compile_capability_requirements(route).material)
    honest = water_leaf and _micro_assess(route, _micro_profile()).material.status is not CapabilityStatus.FIT

    def any_earlier_product(r):
        produced, out = set(), []
        for s_index, st in enumerate(r.steps, start=1):
            seen = set()
            for m in st.reactants:
                key = requirements_mod._species_ident(m)
                if key in produced or key in seen:
                    continue
                seen.add(key)
                out.append((s_index, m))
            produced.update(requirements_mod._species_ident(p) for p in st.products)
        return out

    with _patch(requirements_mod, "_external_inputs", any_earlier_product):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M164", "a species listed under its NAME is treated as provably ABSENT (D24.8 C6)",
        "assess._edge (name-key UNKNOWN branch)")
def m164():
    profile = _profile(material_inventory=(_bottle("ethanol-name-only", "ethanol"),))
    req = _mreq(identity=_ETHANOL, name="ethanol")
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_edge = _src_mutant(assess_mod._edge, ("if name_key is not None:", "if False:"))
    with _patch(assess_mod, "_edge", bad_edge):
        bad = _mat(profile, req) is CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M165", "'distillation apparatus' is read as a FRACTIONAL still (D24.16 F1)",
        "equipment_resolver._APPARATUS_ALIASES")
def m165():
    """The page says "the distillation apparatus as described by your instructor" -- configuration unknown. Honest: the
    string is UNRECOGNIZED -> equipment UNKNOWN on a simple-still bench. Mutant (the Round-III alias restored): a
    FRACTIONAL demand -> the simple-still bench is falsely BLOCKED."""
    route = _micro_route(extra_ops=(_op(OperationKind.DISTILL, apparatus=("distillation apparatus",)),))
    honest = (equipment_resolver_mod.resolve_apparatus("distillation apparatus") is None
              and _equip(route, EquipmentCapability.SIMPLE_DISTILLATION) is CapabilityStatus.UNKNOWN)
    aliases = dict(equipment_resolver_mod._APPARATUS_ALIASES)
    aliases["distillation apparatus"] = EquipmentCapability.FRACTIONAL_DISTILLATION
    with _patch(equipment_resolver_mod, "_APPARATUS_ALIASES", aliases):
        bad = _equip(route, EquipmentCapability.SIMPLE_DISTILLATION) is CapabilityStatus.BLOCKED
    return honest, bad


@mutant("M166", "a step with NO ProcedureEvidence reads equipment/measurement NOT_APPLICABLE (D24.17)",
        "requirements._equipment_requirement + _measurement_requirement (no-procedure notes)")
def m166():
    step = ExperimentStep(STEP_SCHEMA, _MEOAC, (_ACETIC, _METHANOL), (_MEOAC, _WATER), (), ConditionEnvelope())
    route = ExperimentRoute(ROUTE_SCHEMA, (step,))

    def axes():
        a = _micro_assess(route, _micro_profile())
        return a.equipment.status, a.measurement.status

    honest = axes() == (CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN)
    bad_eq = _src_mutant(requirements_mod._equipment_requirement, (
        'unread.append(f"step {s_index} has no ProcedureEvidence: its equipment demand is unread (D24.17)")', "pass"))
    bad_me = _src_mutant(requirements_mod._measurement_requirement, (
        'unread.append(f"step {s_index} has no ProcedureEvidence: its verification demand is unread (D24.17)")',
        "pass"))
    with _patch(requirements_mod, "_equipment_requirement", bad_eq), \
            _patch(requirements_mod, "_measurement_requirement", bad_me):
        bad = axes() == (CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.NOT_APPLICABLE)
    return honest, bad


def _clamped_one() -> IntervalEvidence:
    loc = "fixture: titration assay quoted as 100-101%"
    return IntervalEvidence.build(
        kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "100", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, loc),
                TypedInput("high", "101", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, loc)),
        source_locators=(loc,), domain_of_validity="an assay reading above 100%")


@mutant("M167", "a CLAMPED range collapsed onto a bound certifies a composition (D24.7 C4)",
        "material_spec._compare_composition (degenerate CLAMPED)")
def m167():
    bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "ethanol-clamped", "ethanol",
                           (MaterialComponent.evidenced(_ETHANOL, "active", _clamped_one()),), Phase.LIQUID, "fixture",
                           quantity=StockQuantity.of("500", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
    req = _mreq(identity=_ETHANOL, spec=_floor_spec("0.9"))
    profile = _profile(material_inventory=(bottle,))
    honest = _mat(profile, req) is CapabilityStatus.UNKNOWN
    bad_cmp = _src_mutant(spec_mod._compare_composition, (
        "if stock.interval_evidence is EvidenceKind.CLAMPED and slo == shi and slo in (0, 1):", "if False:"))
    with _patch(spec_mod, "_compare_composition", bad_cmp):
        bad = _mat(profile, req) is CapabilityStatus.FIT
    return honest, bad


@mutant("M168", "every phase mismatch VIOLATES, ignoring the subset relation (D24.7 C5)",
        "material_spec._phase_relation (AQUEOUS_SOLUTION within LIQUID)")
def m168():
    """Leg 1: a SOURCE_QUOTED AQUEOUS_SOLUTION demand vs a USER_DECLARED LIQUID pure bottle -- overlapping, unsettled ->
    UNKNOWN (mutant: BLOCKED, a false refutation). Leg 2: a LIQUID demand vs an AQUEOUS_SOLUTION pure bottle -- an
    aqueous solution IS a liquid -> FIT (mutant: BLOCKED)."""
    def leg(demand, held):
        profile = _profile(material_inventory=(_bottle("ethanol-pure", _ETHANOL, phase=held),))
        return _mat(profile, _mreq(identity=_ETHANOL, phase=PhaseClaim(demand, EvidenceKind.SOURCE_QUOTED)))

    def legs():
        return leg(Phase.AQUEOUS_SOLUTION, Phase.LIQUID), leg(Phase.LIQUID, Phase.AQUEOUS_SOLUTION)

    h1, h2 = legs()
    honest = h1 is CapabilityStatus.UNKNOWN and h2 is CapabilityStatus.FIT
    with _patch(spec_mod, "_phase_relation", lambda required, held: "within" if held is required else "disjoint"):
        b1, b2 = legs()
    return honest, b1 is CapabilityStatus.BLOCKED and b2 is CapabilityStatus.BLOCKED


@mutant("M169", "a pre-rounding recompute-path helper drifts undetected (D24.9 C3)",
        "derived_evidence.KERNEL_KNOWN_ANSWERS (beyond-precision vectors)")
def m169():
    """Adversary C's drift: ``TypedInput.exact`` rounds half-even to PRECISION_DP before the kernel runs, so a quoted
    0.9999995 mints SOURCE_QUOTED [1, 1] -- a 'pure' witness from a certificate that proves nothing of the sort.
    Honest: the beyond-precision vectors refuse the drift at import time (and the shipped V1 keeps [0.999999, 1] ->
    the bottle is UNKNOWN). Mutant: those vectors are removed -> the drift replays clean AND the forged-pure bottle
    FITs."""
    from decimal import ROUND_HALF_EVEN, Decimal

    def drifted_exact(self):
        return Fraction(Decimal(self.value).quantize(Decimal(1).scaleb(-derived_mod.PRECISION_DP), ROUND_HALF_EVEN))

    def verifies() -> bool:
        try:
            derived_mod.verify_kernel_known_answers()
            return True
        except RuntimeError:
            return False

    def near_pure_bottle() -> StockMaterial:
        loc = "fixture: a CoA quoting 0.9999995"
        ev = IntervalEvidence.build(
            kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, basis=ConcentrationBasis.MASS_FRACTION,
            inputs=tuple(TypedInput(n, "0.9999995", InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, loc)
                         for n in ("low", "high")),
            source_locators=(loc,), domain_of_validity="a certificate quoting 7 decimals")
        return StockMaterial(STOCK_MATERIAL_SCHEMA, "ethanol-coa", "ethanol",
                             (MaterialComponent.evidenced(_ETHANOL, "active", ev),), Phase.LIQUID, "fixture",
                             quantity=StockQuantity.of("500", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)

    req = _mreq(identity=_ETHANOL)
    honest_bottle = _mat(_profile(material_inventory=(near_pure_bottle(),)), req) is CapabilityStatus.UNKNOWN
    with _patch(TypedInput, "exact", property(drifted_exact)):
        caught = not verifies()
        beyond = tuple(v for v in derived_mod.KERNEL_KNOWN_ANSWERS if "beyond-precision" not in v.label)
        assert len(beyond) < len(derived_mod.KERNEL_KNOWN_ANSWERS)
        with _patch(derived_mod, "KERNEL_KNOWN_ANSWERS", beyond):
            bad = verifies() and _mat(_profile(material_inventory=(near_pure_bottle(),)), req) is CapabilityStatus.FIT
    return honest_bottle and caught, bad


def _kernel_lock_module():
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "tests" / "test_v0_9_kernel_semantic_lock.py"
    spec = importlib.util.spec_from_file_location("_kernel_semantic_lock_pins", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@mutant("M170", "two kernels swap functions undetected (D24.9 qualified kernel->fn map)",
        "tests/test_v0_9_kernel_semantic_lock.PINNED_KERNEL_FUNCTIONS")
def m170():
    """Honest (D24.9): the kernel->function map is pinned by module-QUALIFIED name, so pointing IDENTITY_SOURCE_QUOTED_V1
    at the band kernel's arithmetic is caught while the shipped map matches. Mutant (the pre-D24.9 check: the SET of
    function ``__name__`` s) -> the swap leaves the name set unchanged and passes."""
    lock = _kernel_lock_module()
    key = DerivationKernel.IDENTITY_SOURCE_QUOTED_V1

    def qualified_map():
        return {k.name: lock._qualified(derived_mod.KERNELS[k].fn) for k in DerivationKernel}

    def name_set():
        return {spec.fn.__name__ for spec in derived_mod.KERNELS.values()}

    shipped_ok, shipped_names = qualified_map() == lock.PINNED_KERNEL_FUNCTIONS, name_set()
    with _patch_item(derived_mod.KERNELS, key, dc.replace(derived_mod.KERNELS[key], fn=derived_mod._k_band)):
        swap_caught = qualified_map() != lock.PINNED_KERNEL_FUNCTIONS
        bad = name_set() == shipped_names
    return shipped_ok and swap_caught, bad


@mutant("M171", "the IR's identity losses are trusted, not re-derived from the request (D24.11 D-L1)",
        "service.CompilationResponse._check_identity_loss_coherence")
def m171():
    """A keyless producer strips the stereochemistry loss of ``C[C@H](O)CC`` (the request is built honestly first) and
    serializes CANONICAL: every public pin recomputed, the consumer pins its own request digest. Honest: REFUSED (the
    losses the carried request implies are re-derived). Mutant: the equality is severed -> the stripped IR loads."""
    import smartchem.identity as identity_mod
    req = build_recompile_request("smiles:C[C@H](O)CC", max_depth=2)
    with _patch(identity_mod, "representation_losses_for", lambda target_input, features: ()):
        forged = run_compilation(req)
    assert forged.compilation_ir is not None and forged.compilation_ir.identity_losses == ()
    payload = response_to_payload(forged)
    _l, err = _try_load(payload, expected_request_digest=req.semantic_digest)
    honest = err is not None and "D24.11" in err
    bad_chk = _src_mutant(CompilationResponse._check_identity_loss_coherence, (
        "if any(losses != expected for losses in carried):", "if False:"))
    with _patch(CompilationResponse, "_check_identity_loss_coherence", bad_chk):
        loaded, _err = _try_load(payload, expected_request_digest=req.semantic_digest)
    bad = loaded is not None and loaded.identity_losses == ()
    return honest, bad


@mutant("M172", "the capability render shows only the free-text label, not the content identity (D24.12)",
        "service.render_capability_lines (label@profile_digest)")
def m172():
    a = _fast_profile_response().ranked_route_dossiers[0].capability_assessment
    honest = a.profile_digest[:12] in svc.render_capability_lines(a, "poor-man", indent="")[0]
    bad_render = _src_mutant(svc.render_capability_lines, (
        "label = f\"{origin or 'profile'}@{assessment.profile_digest[:12]}\"", "label = f\"{origin or 'profile'}\""))
    bad = a.profile_digest[:12] not in bad_render(a, "poor-man", indent="")[0]
    return honest, bad


@mutant("M173", "a capability profile rides a convergent-DAG response that is not REFUSED (D24.13)",
        "service.CompilationResponse._check_capability_topology")
def m173():
    """The producer refuses a capability profile with the convergent-DAG grammar BEFORE searching. A keyless attacker
    grafts a poor-man snapshot onto a genuine convergent response (every public pin recomputed). Honest: REFUSED.
    Mutant: the loader stops mirroring the producer -> a capability question 'answered' with nothing loads."""
    resp = run_compilation(build_recompile_request(_FAST_TARGET, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                                   max_depth=2))
    bad_topo = _src_mutant(CompilationResponse._check_capability_topology, (
        "if request.capability_profile is None or request.transform_grammar is not "
        "TransformGrammar.CAPPED_SCISSION_CONVERGENT:\n        return",
        "if True:\n        return"))
    with _patch(CompilationResponse, "_check_capability_topology", bad_topo):
        payload = response_to_payload(dc.replace(resp, request=dc.replace(
            resp.request, capability_profile=poor_man(), capability_profile_origin="poor-man")))
    _l, err = _try_load(payload)
    honest = err is not None and "D24.13" in err
    with _patch(CompilationResponse, "_check_capability_topology", bad_topo):
        loaded, _err = _try_load(payload)
    bad = (loaded is not None and loaded.request.capability_profile is not None
           and loaded.outcome.value != "REFUSED")
    return honest, bad


@mutant("M174", "a ranked dossier is DELETED and the answer still loads (D24.14 D-D1)",
        "service.CompilationResponse._check_dossier_completeness (ranked == IR)")
def m174():
    resp = _fast_profile_response()
    dropped = resp.ranked_route_dossiers[-1]
    bad_chk = _src_mutant(CompilationResponse._check_dossier_completeness, (
        "if ranked_routes != route_candidates:", "if False:"))
    with _patch(CompilationResponse, "_check_dossier_completeness", bad_chk):
        payload = response_to_payload(dc.replace(
            resp, ranked_route_dossiers=resp.ranked_route_dossiers[:-1],
            affordability_frontier=tuple(e for e in resp.affordability_frontier
                                         if e.route_digest != dropped.route_digest)))
    _l, err = _try_load(payload)
    honest = err is not None and "D24.14" in err
    with _patch(CompilationResponse, "_check_dossier_completeness", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and all(d.route_digest != dropped.route_digest for d in loaded.ranked_route_dossiers)
    return honest, bad


@mutant("M175", "a capability profile embeds the LEGACY physical-bounds-v1alpha1 box (D24.15 D-B2)",
        "profile.CapabilityProfile.__post_init__ (current PhysicalBounds generation only)")
def m175():
    import smartchem.constraints as constraints_mod
    legacy_box = PhysicalBounds(constraints_mod.PHYSICAL_BOUNDS_SCHEMA_V1, 400.0)
    current_box = PhysicalBounds.of(max_temperature_k=400.0)

    def build(box):
        return custom(profile_id="pb-generation-probe", physical_bounds=box)

    try:
        build(legacy_box)
        honest = False
    except ValueError:
        honest = build(current_box).physical_bounds.schema_version == constraints_mod.PHYSICAL_BOUNDS_SCHEMA
    bad_init = _src_mutant(CapabilityProfile.__post_init__, (
        "if self.physical_bounds.schema_version != PHYSICAL_BOUNDS_SCHEMA:", "if False:"))
    with _patch(CapabilityProfile, "__post_init__", bad_init):
        try:  # two content-identical benches, two profile digests (split identity)
            bad = build(legacy_box).profile_digest != build(current_box).profile_digest
        except ValueError:
            bad = False
    return honest, bad


# =================================================================================================================
# M176-M187 (Round V X-high, Wave-C'' fresh non-author confirmation pass -> barrier amendments D25 + D26)
# =================================================================================================================

_NAME_CARRIER = "methanol + 2 g sodium metal in a sealed tube at 650 K"


@mutant("M176", "a demand smuggled into an identity-bearing use NAME is read by nothing (D25.1 NEW-1)",
        "requirements._material_unresolved (name resolves to its own identity)")
def m176():
    """The canonical renderers build from use NAMES and an identity-bearing name was read by nothing. Honest: a name
    that is not a resolvable NAME of its own identity is an unread material demand -> material UNKNOWN. Mutant: the
    name check is severed -> the carrier's extra words vanish -> FIT."""
    uses = (_use(_NAME_CARRIER, ProcedureMaterialRole.SUBSTRATE, identity=_METHANOL, qty="10", phase=Phase.LIQUID),
            _MICRO_BASE_USES[1])
    route = _micro_route(base_uses=uses)
    honest = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.UNKNOWN
    bad_mu = _src_mutant(requirements_mod._material_unresolved, (
        "and not name_resolves_to(use.name, use.identity)):", "and False):"))
    with _patch(requirements_mod, "_material_unresolved", bad_mu):
        bad = _micro_assess(route, _micro_profile()).material.status is CapabilityStatus.FIT
    return honest, bad


@mutant("M177", "a self-contradictory whole bottle certifies a composition (D25.2 NEW-2)",
        "stock.StockMaterial.__post_init__ (whole-material lower bound vs any positive second species)")
def m177():
    """acetic acid [1, 1] w/w beside 0.3 g/mL NaCl: the composition path (not the pure witness) read only the matched
    species. Honest: the bottle is REFUSED at construction. Mutant: the D25.2 check is severed -> the bottle builds and
    certifies a >= 0.99 w/w demand -> FIT."""
    parts = (MaterialComponent.evidenced(_ACETIC, "active", _ev("1", "1")),
             MaterialComponent.evidenced("sodium chloride", "solute",
                                         _ev("0.3", "0.3", basis=ConcentrationBasis.MASS_PER_VOLUME)))

    def build():
        return StockMaterial(STOCK_MATERIAL_SCHEMA, "acid-plus-salt", "acid (with salt)", parts, Phase.LIQUID,
                             "fixture", quantity=StockQuantity.of("500", "mL"),
                             phase_evidence=EvidenceKind.USER_DECLARED)

    req = _mreq(identity=_ACETIC, spec=MaterialSpecification(composition=_comp("0.99", "1", tol=Tolerance.FLOOR)))
    try:
        build()
        honest = False
    except ValueError as exc:
        honest = "D25.2" in str(exc)
    bad_init = _src_mutant(StockMaterial.__post_init__, ("if whole == 1 and any(", "if False and any("))
    with _patch(StockMaterial, "__post_init__", bad_init):
        bad = _mat(_profile(material_inventory=(build(),)), req) is CapabilityStatus.FIT
    return honest, bad


def _forge(resp, **fields):
    """The keyless attacker's in-memory forgery: a copy with fields swapped, never re-running __post_init__."""
    forged = copy.copy(resp)
    for name, value in fields.items():
        object.__setattr__(forged, name, value)
    return forged


@mutant("M178", "a route deleted with its IR candidate + frontier entry still loads (D25.3 NEW-3)",
        "service.CompilationResponse._check_dossier_completeness (candidates == receipt results_returned)")
def m178():
    resp = _fast_profile_response()
    gone = resp.ranked_route_dossiers[0].route_digest
    keep = resp.ranked_route_dossiers[1:]
    ir = dc.replace(resp.compilation_ir, candidates=tuple(
        c for c in resp.compilation_ir.candidates if c.candidate_digest != gone))
    # a CONSISTENT forger (since X-high D27.4 re-derives them): the producer's own frontier over the kept routes
    frontier = svc._route_frontier(resp.request, tuple(svc._reconstruct_route(d.replay_payload) for d in keep), keep)
    payload = response_to_payload(_forge(resp, compilation_ir=ir, ranked_route_dossiers=keep,
                                         affordability_frontier=frontier))
    _l, err = _try_load(payload)
    honest = err is not None and "D25.3" in err
    bad_chk = _src_mutant(CompilationResponse._check_dossier_completeness, (
        "and len(ir.candidates) != receipt.results_returned):", "and False):"))
    with _patch(CompilationResponse, "_check_dossier_completeness", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and all(d.route_digest != gone for d in loaded.ranked_route_dossiers)
    return honest, bad


@mutant("M179", "a NAMELESS leaf requirement treats a name-keyed listing of its species as ABSENT (D25.4 C6)",
        "assess._listed_by_name_only (resolved name keys)")
def m179():
    """The projection's leaf requirements carry NO name, so D24.8 never fired on the real path. Honest: a name-keyed
    'acetic acid' bottle RESOLVES to the untyped leaf's structure -> a possible source -> UNKNOWN. Mutant: resolved name
    keys are ignored -> provable absence -> BLOCKED."""
    route = _micro_route(base_uses=_MICRO_BASE_USES[:1])  # acetic acid is an UNTYPED (nameless) leaf
    profile = _micro_profile(material_inventory=(_bottle("methanol-pure", _METHANOL), _bottle("acid-by-name", "acetic acid")))
    honest = _micro_assess(route, profile).material.status is CapabilityStatus.UNKNOWN
    bad_named = _src_mutant(assess_mod._listed_by_name_only, (
        "if is_structure_key(key) or not name_resolves_to(key, requirement.identity):",  # 0.9.5 S7 (A2)
        "if True:"))
    with _patch(assess_mod, "_listed_by_name_only", bad_named):
        bad = _micro_assess(route, profile).material.status is CapabilityStatus.BLOCKED
    return honest, bad


_Y_TARGET = "smiles:CCOC(C)=O"  # ethyl acetate: the SECOND small search the transplant mutants carry under request X
_Y_CACHE: list = []


def _y_response():
    if not _Y_CACHE:
        _Y_CACHE.append(run_compilation(build_recompile_request(
            _Y_TARGET, capability_profile=isopentyl_capability_fit_bench(), max_depth=2)))
    return _Y_CACHE[0]


@mutant("M180", "a response answers a DIFFERENT request than it carries (D26.1 T1 -- the whole law)",
        "service.CompilationResponse._check_request_answer_coherence")
def m180():
    """T1: request X (methyl acetate) carrying search Y's (ethyl acetate) IR + dossiers, every public pin recomputed.
    Honest: REFUSED (the IR context and the replayed routes are re-derived from the carried request). Mutant: the whole
    D26.1 law is severed -> the transplant loads under the consumer's request pin."""
    x, y = _fast_profile_response(), _y_response()
    payload = response_to_payload(_forge(y, request=x.request))
    _l, err = _try_load(payload, expected_request_digest=x.request.semantic_digest)
    honest = err is not None and "D26.1" in err
    with _patch(CompilationResponse, "_check_request_answer_coherence", lambda self: None):
        loaded, _err = _try_load(payload, expected_request_digest=x.request.semantic_digest)
    bad = loaded is not None and loaded.compilation_ir.target != x.compilation_ir.target
    return honest, bad


@mutant("M181", "a cosmetic transplant (IR context copied) is caught only at the replay -- replay leg severed (D26.1 T1c)",
        "service.CompilationResponse._check_request_answer_coherence (replayed target + terminal-set legs)")
def m181():
    x, y = _fast_profile_response(), _y_response()
    irx, iry = x.compilation_ir, y.compilation_ir
    receipt = dc.replace(iry.search_receipt, target_identity_digest=irx.search_receipt.target_identity_digest,
                         terminal_policy_digest=irx.search_receipt.terminal_policy_digest)
    # the IR's diagnostics stay Y's: since X-high D28.2 they are re-derived from the IR's OWN search status (Y's
    # PARTIAL_DEPTH_LIMIT), so copying X's (COMPLETE) would only be a sloppier forgery that D28.2 refuses first
    ir = dc.replace(iry, target=irx.target, request_digest=irx.request_digest,
                    terminal_policy_digest=irx.terminal_policy_digest, search_receipt=receipt)
    payload = response_to_payload(_forge(y, request=x.request, compilation_ir=ir))
    _l, err = _try_load(payload)
    honest = err is not None and "does not make the requested target" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        "if _structure_ident(replayed.final_target) != ctx.target_ident:", "if False:"), ("if extra:", "if False:"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None
    return honest, bad


def _legacy_rehash(wire: dict) -> dict:
    """Recompute a hand-patched LEGACY wire's derived fields under the FROZEN v0.8 rule (the codec refuses to emit
    legacy, so the attacker patches JSON and rebuilds exactly what the loader reconstructs)."""
    r = CompilationResponse(
        wire["schema_version"], request_from_payload(wire["request"]), svc.ResponseOutcome(wire["outcome"]),
        wire["standard_status"], svc.ir_from_payload(wire["compilation_ir"]), tuple(wire["diagnostics"]),
        tuple(ranked_summary_from_payload(x) for x in wire["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in wire["affordability_frontier"]),
        parse_receipt_summary=wire["parse_receipt_summary"])
    wire["exit_code"] = r.exit_code
    wire["process_selection_status"] = r.process_selection_status
    wire["admissible_route_digests"] = list(r.admissible_route_digests)
    wire["result_digest"] = svc._transport_bound_result_digest(r.result_digest, wire["transport_mode"])
    return wire


@mutant("M182", "a dossier's equation label is not its replayed route's own rendering (D26.1 label leg)",
        "service.CompilationResponse._check_request_answer_coherence (equation label)")
def m182():
    """On a CURRENT payload the D26.1 label leg is backstopped by D27.4 (the re-derived summary carries the rendering)
    and D27.7 (the IR label), so the leg is isolated on the LEGACY wire, where the ranking is v0.8's (D27.4 skipped):
    a real v0.8 dossier + its IR candidate relabelled consistently, derived fields rehashed under the frozen rule."""
    wire = _v08("response_ethyl_acetate_smiles.json")
    lie = "step 1: C7H14O2 -> a route this dossier is not"
    victim = wire["ranked_route_dossiers"][0]
    victim["equation"] = lie
    for c in wire["compilation_ir"]["candidates"]:
        if c["candidate_digest"] == victim["route_digest"]:
            c["equation"] = lie
    payload = _legacy_rehash(wire)
    _l, err = _try_load(payload)
    honest = err is not None and "equation label" in err and "legacy v0.8" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        "if dossier.equation != render(replayed):", "if False:"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and loaded.ranked_route_dossiers[0].equation == lie
    return honest, bad


@mutant("M183", "a consistent deletion (receipt rewritten too) passes opt-in re-execution (D26.2 T2)",
        "service._check_reexecution")
def m183():
    """T2b: delete EVERY candidate and relabel the search COMPLETE (a forged 'no route in the declared space') -- no
    load-time re-derivation can see it. Honest: ``require_reexecution=True`` re-runs the deterministic search and
    REFUSES. Mutant: the result comparison is severed -> the forged NO_ROUTE answer loads under re-execution."""
    from smartchem.compilation_ir import recompile_ir_diagnostics
    from smartchem.search import SearchStatus

    resp = _fast_profile_response()
    ir, req = resp.compilation_ir, resp.request
    receipt = dc.replace(ir.search_receipt, status=SearchStatus.COMPLETE_WITHIN_BOUNDS.value,
                         standard_status=SearchStatus.COMPLETE_WITHIN_BOUNDS.standard_name, results_returned=0,
                         candidate_enumeration_complete=True, cut_enumeration_complete=True,
                         result_limit_saturated=False, stop_reason="")
    # the CONSISTENT forger writes the producer's own no-route diagnostic too (X-high D28.2 re-derives it)
    diagnostics = recompile_ir_diagnostics(
        target_in_terminal_stock=False, complete_within_bounds=True, status_value=receipt.status,
        has_candidates=False, mode=svc._GRAMMAR_TO_MODE[req.transform_grammar],
        max_depth=req.search_bounds.value("max_depth"))
    ir3 = dc.replace(ir, candidates=(), search_status=SearchStatus.COMPLETE_WITHIN_BOUNDS,
                     standard_status=SearchStatus.COMPLETE_WITHIN_BOUNDS.standard_name, search_receipt=receipt,
                     diagnostics=diagnostics)
    payload = response_to_payload(_forge(resp, compilation_ir=ir3, ranked_route_dossiers=(), affordability_frontier=(),
                                         outcome=svc.ResponseOutcome.NO_ROUTE_COMPLETE,
                                         standard_status=ir3.standard_status, diagnostics=diagnostics))
    plain, _perr = _try_load(payload)
    _l, err = _try_load(payload, require_reexecution=True)
    honest = plain is not None and err is not None and "D26.2" in err   # the boundary loads; re-execution refuses
    # both re-execution comparisons severed (the result identity AND, since X-high D27.2, the whole body -- M190
    # isolates the body leg alone)
    bad_re = _src_mutant(svc._check_reexecution, ("if rerun.result_digest != response.result_digest:", "if False:"),
                         ("if _payload_body_digest(rerun_payload) != _payload_body_digest(payload):", "if False:"))
    with _patch(svc, "_check_reexecution", bad_re):
        loaded, _err = _try_load(payload, require_reexecution=True)
    bad = loaded is not None and not loaded.ranked_route_dossiers
    return honest, bad


@mutant("M184", "a capability profile rides a DECOMPILE request (answered with nothing) (D26.3 T4a)",
        "service.CompilationRequest.__post_init__ (no profile on DECOMPILE)")
def m184():
    dreq = svc.build_decompile_request("C7H14O2")

    def attach():
        return dc.replace(dreq, capability_profile=poor_man(), capability_profile_origin=poor_man().profile_id)

    try:
        attach()
        honest = False
    except ValueError as exc:
        honest = "D26.3" in str(exc)
    bad_init = _src_mutant(CompilationRequest.__post_init__, (
        "if self.capability_profile is not None and self.operation is CompilationOperation.DECOMPILE:", "if False:"))
    with _patch(CompilationRequest, "__post_init__", bad_init):
        try:
            bad = attach().capability_profile is not None
        except ValueError:
            bad = False
    return honest, bad


@mutant("M185", "a legacy v0.8 request is re-serialized with 0.9-only keys under the v0.8 id (D26.5 T6b)",
        "service.request_to_payload (legacy refusal)")
def m185():
    legacy = request_from_payload(_v08("request_isopentyl_acetate.json"))
    try:
        request_to_payload(legacy)
        honest = False
    except ValueError as exc:
        honest = legacy.is_legacy_v08 and "D26.5" in str(exc)
    bad_enc = _src_mutant(svc.request_to_payload, ("    if request.is_legacy_v08:\n", "    if False:\n"))
    with _patch(svc, "request_to_payload", bad_enc):
        emitted = svc.request_to_payload(legacy)
    bad = emitted["schema_version"] == legacy.schema_version and "capability_profile" in emitted
    return honest, bad


@mutant("M186", "a canonical node MISSING a field decodes default-filled (D26.6 B5)",
        "service._decode_canonical (exact field set)")
def m186():
    payload = request_to_payload(build_recompile_request(_FAST_TARGET, max_depth=2, capability_profile="poor-man"))
    profile = copy.deepcopy(payload["capability_profile"])
    stack, box = [profile], None
    while stack and box is None:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("class") == "smartchem.constraints.PhysicalBounds":
                box = node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    box["fields"] = [f for f in box["fields"] if f[0] != "min_temperature_k"]
    try:
        svc._capability_profile_from_payload(copy.deepcopy(profile))
        honest = False
    except ValueError as exc:
        honest = "D26.6" in str(exc) and poor_man().physical_bounds.min_temperature_k is not None
    bad_dec = _src_mutant(svc._decode_canonical, (
        "if sorted(carried) != expected or len(carried) != len(set(carried)):", "if False:"))
    with _patch(svc, "_decode_canonical", bad_dec):
        try:
            bad = svc._capability_profile_from_payload(copy.deepcopy(profile)).physical_bounds.min_temperature_k is None
        except ValueError:
            bad = False
    return honest, bad


@mutant("M187", "a reaction-centre payload of ANOTHER version is silently relabelled current (D26.7 RC-v)",
        "reaction_center.ReactionCenter.from_payload (schema_version)")
def m187():
    from smartchem.reaction_center import REACTION_CENTER_SCHEMA, ReactionCenter

    bogus = dict(ReactionCenter.of((("C", "O", 1),), (("C", "O", 1),), 1).to_payload(),
                 schema_version="smartchem/reaction-center-v0-bogus")
    try:
        ReactionCenter.from_payload(bogus)
        honest = False
    except ValueError as exc:
        honest = "D26.7" in str(exc)
    bad_dec = _src_mutant(ReactionCenter.from_payload, (
        'if payload["schema_version"] != REACTION_CENTER_SCHEMA:', "if False:"))
    with _patch(ReactionCenter, "from_payload", bad_dec):
        try:
            bad = ReactionCenter.from_payload(bogus).schema_version == REACTION_CENTER_SCHEMA
        except ValueError:
            bad = False
    return honest, bad


# -- X-high D27 (Wave C4 C4T-1..8 + Foreman N2-N4 + the D27.8 ledger audit): one mutant per law leg --------------------

_D27_CACHE: dict = {}
_BENCH_HELPERS = dict(helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",))
_PROCESS_HELPERS = dict(helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0))


def _d27(name: str):
    """The small honest compilations the D27 forgeries start from (cached; built OUTSIDE any patch context)."""
    if name not in _D27_CACHE:
        builders = {
            "plain": lambda: build_recompile_request(_FAST_TARGET, max_depth=2),
            "bench": lambda: build_recompile_request(_FAST_TARGET, capability_profile=isopentyl_capability_fit_bench(),
                                                     max_depth=2, **_BENCH_HELPERS),
            "process": lambda: build_recompile_request(_FAST_TARGET, max_depth=2, **_PROCESS_HELPERS),
            "dag": lambda: build_recompile_request(_FAST_TARGET, max_depth=2,
                                                   grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, **_PROCESS_HELPERS),
            "coc": lambda: build_recompile_request("smiles:COC", max_depth=1),
        }
        _D27_CACHE[name] = run_compilation(builders[name]())
    return _D27_CACHE[name]


def _public_digest(wire: dict, resp) -> dict:
    """The keyless forger: recompute the PUBLIC whole-body wire digest after a raw edit."""
    wire["result_digest"] = svc._transport_bound_result_digest(resp.result_digest, wire["transport_mode"],
                                                               svc._payload_body_digest(wire))
    return wire


@mutant("M188", "a corpus envelope GRAFTED onto another reaction's step is trusted (D27.1 C4T-1)",
        "service.CompilationResponse._check_corpus_evidence_coherence")
def m188():
    """Honest: the isopentyl corpus envelope grafted onto methyl acetate's esterification (dossier honestly re-derived
    from the tampered route, IR candidate digests rebound) is REFUSED. Mutant: the corpus comparison is severed -> the
    forged PROCESS_SPECIFIED loads."""
    resp = _d27("plain")
    s = structure_by_name
    result = rt.search_routes(s("isopentyl acetate").molecule, reagents=(s("water").molecule, s("acetic acid").molecule),
                              available=(s("isopentyl alcohol").molecule,), max_depth=1)
    donor = next(r.steps[0].envelope for r in result.routes if r.steps[0].envelope.procedure is not None)
    remap, replayed = {}, []
    for d in resp.ranked_route_dossiers:
        route = svc._reconstruct_route(d.replay_payload)
        if len(route.steps) == 1:
            grafted = dc.replace(route, steps=(dc.replace(route.steps[0], envelope=donor),))
            remap[d.route_digest] = grafted.digest
            route = grafted
        replayed.append(route)
    ranked = svc._ranked_summaries(tuple(replayed), resp.request.constraints.bounds, resp.identity_losses)
    ir = resp.compilation_ir
    cands = tuple(sorted((dc.replace(c, candidate_digest=remap.get(c.candidate_digest, c.candidate_digest))
                          for c in ir.candidates), key=lambda c: c.candidate_digest))
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, candidates=cands), ranked_route_dossiers=ranked,
                                         affordability_frontier=svc._affordability_frontier(tuple(replayed), ranked)))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.1" in err
    bad_chk = _src_mutant(CompilationResponse._check_corpus_evidence_coherence, ("if carried != expected:", "if False:"))
    with _patch(CompilationResponse, "_check_corpus_evidence_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and any(d.readiness.tier == PROCESS_SPECIFIED for d in loaded.ranked_route_dossiers)
    return honest, bad


@mutant("M189", "a raw wire edit of a digest-only field loads without recomputing the digest (D27.2 C4T-8)",
        "service._payload_body_digest (the whole-body wire digest)")
def m189():
    """Honest: the parse receipt edited on the wire (nothing recomputed) is refused by the whole-body digest. Mutant: the
    body digest is a constant (the pre-D27.2 identity-only digest) -> the edit loads."""
    resp = _d27("plain")

    def edited():
        wire = response_to_payload(resp)
        wire["parse_receipt_summary"] = f"{wire['parse_receipt_summary']} (FORGED)"
        return wire

    _l, err = _try_load(edited())
    honest = err is not None and "result_digest does not match" in err
    with _patch(svc, "_payload_body_digest", lambda payload: "0" * 64):
        loaded, _err = _try_load(edited())
    bad = loaded is not None and loaded.parse_receipt_summary.endswith("(FORGED)")
    return honest, bad


@mutant("M190", "a NEUTRAL re-centre (outside result identity) passes require_reexecution (D27.2 Foreman N4)",
        "service._check_reexecution (whole-body comparison)")
def m190():
    """Honest: the FORMAL route's step-2 reaction centre re-centred (readiness unchanged, public digest recomputed) is
    refused by re-execution, which compares the whole re-executed body. Mutant: only the result identity is compared.
    X-high D29.1 (a newer, independent law) now refuses this re-centre on EVERY load (M213 pins that), so -- per the
    harness rule -- M190 reads its own layer, re-execution, with D29.1 held out in BOTH arms (never by weakening it)."""
    resp = _d27("plain")
    formal = next(d for d in resp.ranked_route_dossiers if len(d.replay_payload) == 2)
    replay = copy.deepcopy(formal.replay_payload)
    replay[1]["reaction_center"]["n_components"] += 1
    forged = dc.replace(resp, ranked_route_dossiers=tuple(
        dc.replace(d, replay_payload=replay) if d is formal else d for d in resp.ranked_route_dossiers))
    payload = response_to_payload(forged)
    with _patch(CompilationResponse, "_check_replay_step_transforms", lambda self, **_kw: None):
        plain, _perr = _try_load(payload)
        _l, err = _try_load(payload, require_reexecution=True)
        honest = plain is not None and err is not None and "D27.2" in err
        bad_re = _src_mutant(svc._check_reexecution, (
            "if _payload_body_digest(rerun_payload) != _payload_body_digest(payload):", "if False:"))
        with _patch(svc, "_check_reexecution", bad_re):
            loaded, _err = _try_load(payload, require_reexecution=True)
    bad = loaded is not None
    return honest, bad


@mutant("M191", "ROUTES_FOUND relabelled TARGET_ALREADY_AVAILABLE loads (D27.3 C4T-3)",
        "service.CompilationResponse._check_request_answer_coherence (outcome classification)")
def m191():
    honest_resp = _d27("coc")
    payload = response_to_payload(dc.replace(honest_resp, outcome=svc.ResponseOutcome.TARGET_ALREADY_AVAILABLE))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.3" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        "if self.outcome is not expected_outcome:", "if False:"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and loaded.exit_code == 0
    return honest, bad


@mutant("M192", "a REORDERED ranking / dossiers judged under another box load (D27.4 C4T-4 + Foreman N3)",
        "service.CompilationResponse._check_ranking_coherence (whole ranked tuple)")
def m192():
    """Honest: the bench ranking reversed (frontier rebuilt) AND no-box dossiers carried under a 280 K-ceiling request
    are both refused by this leg. Mutant: the ranked-tuple comparison is severed -> the reorder loads.  (The N3
    transplant stays refused under the mutant: the diagnostics leg re-derives the fit tally from the RE-DERIVED ranking
    -- defence in depth, so it cannot witness this leg alone.)"""
    resp = _d27("bench")
    reordered = tuple(reversed(resp.ranked_route_dossiers))
    replayed = tuple(svc._reconstruct_route(d.replay_payload) for d in reordered)
    reorder = response_to_payload(_forge(resp, ranked_route_dossiers=reordered,
                                         affordability_frontier=svc._affordability_frontier(replayed, reordered)))
    x = build_recompile_request(_FAST_TARGET, max_depth=2, max_temperature_k=280.0)
    transplant = response_to_payload(_forge(_d27("plain"), request=x))
    errs = [_try_load(p)[1] for p in (reorder, transplant)]
    honest = all(e is not None and "not the producer's ranking" in e for e in errs)
    bad_chk = _src_mutant(CompilationResponse._check_ranking_coherence, ("if ranked != dossiers:", "if False:"))
    with _patch(CompilationResponse, "_check_ranking_coherence", bad_chk):
        loaded, _err = _try_load(reorder)
    bad = loaded is not None and loaded.ranked_route_dossiers == reordered
    return honest, bad


@mutant("M193", "a DELETED affordability frontier (public digest recomputed) loads (D27.4 C4T-2)",
        "service.CompilationResponse._check_ranking_coherence (frontier leg)")
def m193():
    resp = _d27("bench")
    assert resp.affordability_frontier
    payload = response_to_payload(_forge(resp, affordability_frontier=()))
    _l, err = _try_load(payload)
    honest = err is not None and "affordability_frontier is not the producer's frontier" in err
    bad_chk = _src_mutant(CompilationResponse._check_ranking_coherence, (
        "if _route_frontier(request, routes, ranked) != self.affordability_frontier:", "if False:"))
    with _patch(CompilationResponse, "_check_ranking_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and not loaded.affordability_frontier
    return honest, bad


@mutant("M194", "a FORGED human-visible fit tally in the diagnostics loads (D27.4 C4T-7)",
        "service.CompilationResponse._check_ranking_coherence (diagnostics leg)")
def m194():
    resp = _d27("process")
    note = next(x for x in resp.diagnostics if "section-11 constraint APPLIED" in x)
    fits, excluded, unknown = svc._fit_counts(resp.ranked_route_dossiers)
    tally = f"{fits} FIT, {excluded} EXCLUDED (outside a hard bound), {unknown} UNKNOWN-fit"
    lie = note.replace(tally, f"{fits + unknown} FIT, {excluded} EXCLUDED (outside a hard bound), 0 UNKNOWN-fit")
    assert lie != note
    payload = response_to_payload(_forge(resp, diagnostics=tuple(lie if x == note else x for x in resp.diagnostics)))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.4" in err
    bad_chk = _src_mutant(CompilationResponse._check_ranking_coherence, (
        "if self.diagnostics != tuple(expected_diagnostics):", "if False:"))
    with _patch(CompilationResponse, "_check_ranking_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and lie in loaded.diagnostics
    return honest, bad


@mutant("M195", "the receipt-count bind is LINEAR-only again: a deleted DAG loads (D27.5 C4T-5)",
        "service.CompilationResponse._check_dossier_completeness (every search kind)")
def m195():
    from smartchem.experiment.drafter import ConstraintBox

    resp = _d27("dag")
    ir = resp.compilation_ir
    victim = ir.candidates[0].candidate_digest
    kept = tuple(d for d in resp.ranked_dag_dossiers if d.route_digest != victim)
    # a CONSISTENT forger: the producer's own DAG-bench note over the kept DAGs (D27.4 re-derives the diagnostics)
    box = ConstraintBox.of_bounds(resp.request.constraints.bounds, process=resp.request.constraints.process)
    note = svc._dag_bench_note(tuple(svc._reconstruct_dag(d.replay_payload) for d in kept), box)
    diagnostics = (*resp.diagnostics[:-1], note)
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, candidates=ir.candidates[1:]),
                                         ranked_dag_dossiers=kept, diagnostics=diagnostics))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.5" in err
    bad_chk = _src_mutant(CompilationResponse._check_dossier_completeness, (
        "and len(ir.candidates) != receipt.results_returned):",
        'and receipt.search_kind == "LINEAR_ROUTE" and len(ir.candidates) != receipt.results_returned):'))
    with _patch(CompilationResponse, "_check_dossier_completeness", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and len(loaded.compilation_ir.candidates) < ir.search_receipt.results_returned
    return honest, bad


@mutant("M196", "receipt search bounds that are not the request's load (D27.6 C4T-6)",
        "service.CompilationResponse._check_receipt_bounds (bounds)")
def m196():
    resp = _d27("plain")
    ir = resp.compilation_ir
    inflated = dc.replace(ir, search_receipt=dc.replace(ir.search_receipt, max_depth=12, cut_budget=10**7,
                                                        result_limit=10**4))
    payload = response_to_payload(_forge(resp, compilation_ir=inflated))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.6" in err
    bad_chk = _src_mutant(CompilationResponse._check_receipt_bounds, ("if carried != expected:", "if False:"))
    with _patch(CompilationResponse, "_check_receipt_bounds", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and loaded.compilation_ir.search_receipt.max_depth == 12
    return honest, bad


@mutant("M197", "a depth-2 route under a max_depth=1 request (receipt rewritten to match) loads (D27.6 Foreman N2)",
        "service.CompilationResponse._check_request_answer_coherence (per-route depth leg)")
def m197():
    resp = _d27("plain")
    x1 = build_recompile_request(_FAST_TARGET, max_depth=1)
    ir = resp.compilation_ir
    ir1 = dc.replace(ir, request_digest=svc._rederive_request_context(x1).request_digest,
                     search_receipt=dc.replace(ir.search_receipt, max_depth=1))
    payload = response_to_payload(_forge(resp, request=x1, compilation_ir=ir1))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.6" in err and "steps" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        'if kind == "route" and len(replayed.steps) > request.search_bounds.value("max_depth"):', "if False:"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and max(len(d.replay_payload) for d in loaded.ranked_route_dossiers) > 1
    return honest, bad


@mutant("M198", "a receipt relabelled to another search KIND loads (D27.6/D27.8 ledger audit)",
        "service.CompilationResponse._check_receipt_bounds (kind + cut-budget scope)")
def m198():
    resp = _d27("plain")
    ir = resp.compilation_ir
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, search_receipt=dc.replace(
        ir.search_receipt, search_kind="CONVERGENT_DAG"))))
    _l, err = _try_load(payload)
    honest = err is not None and "relabelled receipt" in err
    bad_chk = _src_mutant(CompilationResponse._check_receipt_bounds, (
        "if (receipt.search_kind, receipt.cut_budget_scope) != (kind, _SERVICE_RECEIPT_CUT_BUDGET_SCOPE):", "if False:"))
    with _patch(CompilationResponse, "_check_receipt_bounds", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and loaded.compilation_ir.search_receipt.search_kind == "CONVERGENT_DAG"
    return honest, bad


@mutant("M199", "an IR candidate's free-text equation contradicts its dossier (D27.7 C4T-8)",
        "service.CompilationResponse._check_request_answer_coherence (IR candidate label)")
def m199():
    resp = _d27("bench")
    ir = resp.compilation_ir
    best = resp.ranked_route_dossiers[0].equation
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, candidates=tuple(
        dc.replace(c, equation=best) for c in ir.candidates))))
    _l, err = _try_load(payload)
    honest = err is not None and "D27.7" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        "and candidate_equations[dossier.route_digest] != dossier.equation):", "and False):"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and all(c.equation == best for c in loaded.compilation_ir.candidates)
    return honest, bad


@mutant("M200", "a CANONICAL_VERIFIED dossier that dropped its replay loads (D27.7 C4T-8)",
        "service.response_from_payload (canonical wire carries every replay)")
def m200():
    resp = _d27("process")
    formal = next(d for d in resp.ranked_route_dossiers if d.readiness.tier == FORMAL_CANDIDATE)
    payload = response_to_payload(_forge(resp, ranked_route_dossiers=tuple(
        dc.replace(d, replay_payload=None) if d is formal else d for d in resp.ranked_route_dossiers)))
    _l, err = _try_load(payload)
    honest = payload["transport_mode"] == "CANONICAL_VERIFIED" and err is not None and "D27.7" in err
    bad_load = _src_mutant(svc.response_from_payload, ("        if bare:\n", "        if False:\n"))
    try:
        loaded = bad_load(copy.deepcopy(payload))
    except ValueError:
        loaded = None
    bad = loaded is not None and any(d.replay_payload is None for d in loaded.ranked_route_dossiers)
    return honest, bad


class _RerunCalled(Exception):
    """Raised by the M201 sentinel: the verifier ran a compile."""


@mutant("M201", "an UNPINNED payload chooses a larger search for its re-execution verifier (D27.7 C4T-8)",
        "service._check_reexecution (unpinned default-bounds ceiling)")
def m201():
    resp = _d27("plain")
    bigger = dc.replace(resp.request, search_bounds=svc.SearchBounds.of(
        **dict(dict(resp.request.search_bounds.bounds), max_depth=6)))
    ir = resp.compilation_ir
    ir6 = dc.replace(ir, request_digest=svc._rederive_request_context(bigger).request_digest,
                     search_receipt=dc.replace(ir.search_receipt, max_depth=6))
    payload = response_to_payload(_forge(resp, request=bigger, compilation_ir=ir6))
    calls: list = []

    def sentinel(request):
        calls.append(request.search_bounds.value("max_depth"))
        raise _RerunCalled

    with _patch(svc, "run_compilation", sentinel):     # installed BEFORE the mutant snapshots the module globals
        _l, err = _try_load(payload, require_reexecution=True)
        honest = err is not None and "D27.7" in err and not calls
        bad_re = _src_mutant(svc._check_reexecution, ("        if over:\n", "        if False:\n"))
        with _patch(svc, "_check_reexecution", bad_re), contextlib.suppress(_RerunCalled):
            _try_load(payload, require_reexecution=True)
    bad = calls == [6]
    return honest, bad


@mutant("M202", "the derived wire key search_space_status is a free label (D27.8 ledger audit)",
        "service.response_from_payload (derived-key round trip)")
def m202():
    resp = _d27("plain")
    wire = response_to_payload(resp)
    wire["search_space_status"] = "NO_ROUTE_IN_DECLARED_SPACE"
    _public_digest(wire, resp)
    _l, err = _try_load(wire)
    honest = err is not None and "search_space_status does not match" in err
    bad_load = _src_mutant(svc.response_from_payload, (
        '"exit_code", "search_space_status"):', '"exit_code"):'))
    try:
        bad_load(copy.deepcopy(wire))
        bad = True
    except ValueError:
        bad = False
    return honest, bad


# -- X-high D28 (Wave C5 transport-ledger audit C5-F1..F7 + the D28.6 forgery sweep): one mutant per law leg ------------

_D28_CACHE: dict = {}
_LEDGER_TESTS: list = []


def _d28(name: str):
    """The honest compilations the D28 forgeries start from (cached; built OUTSIDE any patch context)."""
    if name not in _D28_CACHE:
        builders = {
            # methyl salicylate under a PASSIVE-only process box: its sourced corpus record EXCLUDES it (C5-F1)
            "mesal_passive": lambda: build_recompile_request(
                "smiles:COC(=O)c1ccccc1O", max_depth=1, helper_reagents=("water",),
                stock_materials=("salicylic acid", "methanol"),
                process=ProcessBounds.of(allowed_attention=(Attention.PASSIVE,)), capability_profile="poor-man"),
            # an UNCONSTRAINED convergent-DAG search: DAG candidates with no dossier (C5-F5)
            "free_dag": lambda: build_recompile_request(_FAST_TARGET, max_depth=2,
                                                        grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                                        helper_reagents=("water", "acetic acid")),
        }
        _D28_CACHE[name] = run_compilation(builders[name]())
    return _D28_CACHE[name]


def _ledger_tests():
    """``tests/test_transport_ledger.py`` as a module: the D28.4 docstring cross-check and the D28.6 forgery table ARE
    the defences under test there (a mutant of the ledger is caught by the test, so the harness asks the test)."""
    if not _LEDGER_TESTS:
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "tests" / "test_transport_ledger.py"
        spec = importlib.util.spec_from_file_location("_d28_ledger_tests", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LEDGER_TESTS.append(module)
    return _LEDGER_TESTS[0]


@mutant("M203", "a corpus envelope STRIPPED to unknown() is skipped: a section-11 EXCLUSION reads UNKNOWN (D28.1 C5-F1)",
        "service.CompilationResponse._check_corpus_evidence_coherence (current-payload unknown())")
def m203():
    """Honest: methyl salicylate's sourced envelope stripped to unknown() and the whole answer re-derived from the
    tampered route (ranking, frontier, IR candidates, constraint note) is REFUSED. Mutant: D27.1's carve-out ("an unknown
    envelope claims nothing") widened back to CURRENT payloads -> the forged fit UNKNOWN loads and the REAL_BUT_HARD
    frontier entry is gone."""
    resp = _d28("mesal_passive")
    req, ir = resp.request, resp.compilation_ir
    assert [d.fit_status for d in resp.ranked_route_dossiers] == ["EXCLUDED"]
    remap, replayed = {}, []
    for d in resp.ranked_route_dossiers:
        route = svc._reconstruct_route(d.replay_payload)
        bare = dc.replace(route, steps=tuple(dc.replace(s, envelope=ConditionEnvelope.unknown()) for s in route.steps))
        remap[d.route_digest] = bare.digest
        replayed.append(bare)
    replayed = tuple(replayed)
    ranked = svc._ranked_summaries(replayed, req.constraints.bounds, resp.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    cands = tuple(sorted((dc.replace(c, candidate_digest=remap.get(c.candidate_digest, c.candidate_digest))
                          for c in ir.candidates), key=lambda c: c.candidate_digest))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked), process=req.constraints.process)
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, candidates=cands), ranked_route_dossiers=ranked,
                                         affordability_frontier=svc._route_frontier(req, replayed, ranked),
                                         diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,))))
    _l, err = _try_load(payload)
    honest = err is not None and "D28.1" in err
    bad_chk = _src_mutant(CompilationResponse._check_corpus_evidence_coherence, (
        "if self.is_legacy_v08 and step.envelope == unknown:", "if step.envelope == unknown:"))
    with _patch(CompilationResponse, "_check_corpus_evidence_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = (loaded is not None and [d.fit_status for d in loaded.ranked_route_dossiers] == ["UNKNOWN"]
           and not loaded.affordability_frontier)
    return honest, bad


@mutant("M204", "an INJECTED line in the IR's own diagnostics loads (D28.2 C5-F2, C4T-7 reopened)",
        "service.CompilationResponse._check_request_answer_coherence (IR diagnostics re-derived by the shared helper)")
def m204():
    resp = _d27("plain")
    ir = resp.compilation_ir
    lie = "section-11 constraint APPLIED: 1 FIT, 0 EXCLUDED; CAPABILITY_FIT under poor-man (FORGED)"
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, diagnostics=(lie, *ir.diagnostics)),
                                         diagnostics=(lie, *resp.diagnostics)))
    _l, err = _try_load(payload)
    honest = err is not None and "D28.2" in err
    bad_chk = _src_mutant(CompilationResponse._check_request_answer_coherence, (
        "if tuple(ir.diagnostics) != expected_ir_diagnostics:", "if False:"))
    with _patch(CompilationResponse, "_check_request_answer_coherence", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and lie in loaded.compilation_ir.diagnostics
    return honest, bad


@mutant("M205", "a NULL receipt identity digest slips the present-only compare (D28.3 C5-F3)",
        "service.CompilationResponse._check_receipt_bounds (non-null identity digests)")
def m205():
    resp = _d27("plain")
    ir = resp.compilation_ir
    payload = response_to_payload(_forge(resp, compilation_ir=dc.replace(ir, search_receipt=dc.replace(
        ir.search_receipt, target_identity_digest=None, terminal_policy_digest=None))))
    _l, err = _try_load(payload)
    honest = err is not None and "D28.3" in err
    bad_chk = _src_mutant(CompilationResponse._check_receipt_bounds, (
        "if carried_digest is None or carried_digest != bound:",
        "if carried_digest is not None and carried_digest != bound:"))
    with _patch(CompilationResponse, "_check_receipt_bounds", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and loaded.compilation_ir.search_receipt.target_identity_digest is None
    return honest, bad


@mutant("M206", "a NULL result count hides a deleted candidate (D28.3 C5-F4)",
        "service.CompilationResponse._check_dossier_completeness (results_returned is an int)")
def m206():
    """Honest: the worst-ranked route deleted (dossier + IR candidate, frontier and tally rebuilt) with the receipt's
    count nulled is REFUSED. Mutant: fc710a8's shape -- no int law, the count compare skipped when null -> it loads."""
    resp = _d27("bench")
    req, ir = resp.request, resp.compilation_ir
    keep = resp.ranked_route_dossiers[:-1]
    kept_routes = tuple(svc._reconstruct_route(d.replay_payload) for d in keep)
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(keep), process=req.constraints.process)
    gone = resp.ranked_route_dossiers[-1].route_digest
    forged_ir = dc.replace(ir, candidates=tuple(c for c in ir.candidates if c.candidate_digest != gone),
                           search_receipt=dc.replace(ir.search_receipt, results_returned=None))
    payload = response_to_payload(_forge(resp, compilation_ir=forged_ir, ranked_route_dossiers=keep,
                                         affordability_frontier=svc._route_frontier(req, kept_routes, keep),
                                         diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,))))
    _l, err = _try_load(payload)
    honest = err is not None and "D28.3" in err
    bad_chk = _src_mutant(CompilationResponse._check_dossier_completeness, (
        "if receipt is not None and (isinstance(receipt.results_returned, bool)",
        "if False and (isinstance(receipt.results_returned, bool)"), (
        "and len(ir.candidates) != receipt.results_returned):",
        "and receipt.results_returned is not None and len(ir.candidates) != receipt.results_returned):"))
    with _patch(CompilationResponse, "_check_dossier_completeness", bad_chk):
        loaded, _err = _try_load(payload)
    bad = loaded is not None and len(loaded.ranked_route_dossiers) == len(resp.ranked_route_dossiers) - 1
    return honest, bad


@mutant("M207", "an UNCONSTRAINED DAG candidate's label is advisory but the ledger calls it re-derived (D28.4 C5-F5)",
        "transport_ledger CandidateSummary advisory_when (+ the service docstring cross-check)")
def m207():
    """Honest: the ledger's partially-advisory set is exactly what the service docstring discloses, and the disclosed
    residual (a keyless edit of a dossier-less DAG candidate's equation) really loads. Mutant: the entry's
    ``advisory_when`` dropped -- the ledger claims RE_DERIVED_ON_LOAD unconditionally while the forgery still loads (the
    C5-F5 over-claim), and the docstring cross-check of tests/test_transport_ledger.py flags the mismatch."""
    import smartchem.transport_ledger as ledger

    lt = _ledger_tests()
    wire = response_to_payload(_d28("free_dag"))
    wire["compilation_ir"]["candidates"][0]["equation"] = "C3H6O2 fits your bench: CAPABILITY_FIT (FORGED)"
    loaded, _err = _try_load(lt._reforge(wire))

    def disclosure_mismatch() -> bool:
        doc = svc.__doc__
        partial = doc[doc.index("What a KEYLESS consumer must treat as advisory"):].partition("Partially advisory")[2]
        return {f"{t}.{f}" for t, f in lt._TOKEN.findall(partial)} != set(ledger.partially_advisory_fields())

    honest = loaded is not None and not disclosure_mismatch()
    table = ledger.TRANSPORT_LEDGER["CandidateSummary"]
    with _patch_item(table, "equation", dc.replace(table["equation"], advisory_when="")):
        over_claim = "CandidateSummary.equation" not in ledger.partially_advisory_fields()
        flagged = disclosure_mismatch()
    bad = loaded is not None and over_claim and flagged
    return honest, bad


@mutant("M208", "an UNKNOWN key on a service container rides the digest as unenforced text (D28.5 C5-F6)",
        "service._require_payload_keys (exact keys: response/request/dossier/DAG/frontier/cost vector/snapshot)")
def m208():
    resp = _d27("bench")
    wire = response_to_payload(resp)
    wire["ranked_route_dossiers"][0]["capability_overall"] = "CAPABILITY_FIT"
    wire["request"]["capability_verdict"] = "CAPABILITY_FIT"
    _public_digest(wire, resp)
    _l, err = _try_load(wire)
    honest = err is not None and "D28.5" in err
    with _patch(svc, "_require_payload_keys", lambda *_a, **_k: None):
        loaded, _err = _try_load(wire)
    bad = loaded is not None
    return honest, bad


@mutant("M209", "an UNKNOWN key on an IR container rides the digest as unenforced text (D28.5 C5-F6)",
        "compilation_ir._require_exact_keys (exact keys: IR/target/receipt/candidate)")
def m209():
    import smartchem.compilation_ir as cir_mod

    resp = _d27("bench")
    wire = response_to_payload(resp)
    wire["compilation_ir"]["candidates"][0]["readiness"] = "PROCESS_SPECIFIED"
    wire["compilation_ir"]["search_receipt"]["verified"] = True
    _public_digest(wire, resp)
    _l, err = _try_load(wire)
    honest = err is not None and "D28.5" in err
    with _patch(cir_mod, "_require_exact_keys", lambda *_a, **_k: None):
        loaded, _err = _try_load(wire)
    bad = loaded is not None
    return honest, bad


@mutant("M210", "serial_holds decoded by int()/float() COERCION: a string index loads (D28.5 C5-F7)",
        "service._exact_hold_triple (exact JSON numbers)")
def m210():
    """Honest: a real serial hold (the corpus gains a synthetic declared process, so the convergent DAG discloses
    holds) rewritten with a STRING index that coerces to the honest value is refused. Mutant: fc710a8's coercion."""
    declared = ProcessRequirements(elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
                                   agitation=Agitation.NONE, workup_included=True,
                                   provenance="synthetic software control; no experimental claim")
    original = rt._conditions_for
    with _patch(rt, "_conditions_for", lambda t: dc.replace(original(t), process=declared)):
        resp = run_compilation(build_recompile_request(_FAST_TARGET, max_depth=2,
                                                       grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                                       **_PROCESS_HELPERS))
        wire = response_to_payload(resp)
        k, hold = next((k, h) for k, d in enumerate(wire["ranked_dag_dossiers"]) for h in d["serial_holds"])
        holds = wire["ranked_dag_dossiers"][k]["serial_holds"]
        holds[holds.index(hold)] = [str(hold[0]), hold[1], hold[2]]
        _public_digest(wire, resp)

        def attempt():
            try:
                return response_from_payload(copy.deepcopy(wire)), None
            except (TypeError, ValueError) as exc:
                return None, str(exc)

        _l, err = attempt()
        honest = err is not None and "serial hold" in err
        with _patch(svc, "_exact_hold_triple", lambda t: (int(t[0]), int(t[1]), float(t[2]))):
            loaded, _err = attempt()
    bad = loaded is not None
    return honest, bad


@mutant("M211", "a NON-ADVISORY ledger label without a refusing forgery over-claims silently (D28.6 C5-test)",
        "tests/test_transport_ledger.py forgery sweep (every RE/REQ/FROZEN entry names its keyless forgery)")
def m211():
    """Honest: every non-advisory ledger entry names a keyless forgery (tests/test_transport_ledger.py ``_FORGERIES``).
    Mutant: the receipt's advisory ``stop_reason`` RELABELLED re-derived -- an over-claim (its keyless forgery LOADS) that
    the sweep flags as a label with no refusing forgery."""
    import smartchem.transport_ledger as ledger

    lt = _ledger_tests()

    def unforged() -> set:
        labelled = {f"{t}.{f}" for t, entries in ledger.TRANSPORT_LEDGER.items() for f, e in entries.items()
                    if e.status is not ledger.TransportStatus.DIGEST_ONLY_ADVISORY}
        return labelled - set(lt._FORGERIES)

    wire = response_to_payload(_d27("bench"))            # an INCOMPLETE search: its receipt carries a stop reason
    assert wire["compilation_ir"]["search_receipt"]["stop_reason"]
    wire["compilation_ir"]["search_receipt"]["stop_reason"] = "exhaustive: every route bench-verified (FORGED)"
    loaded, _err = _try_load(lt._reforge(wire))
    honest = not unforged()
    relabel = ledger.LedgerEntry(ledger.TransportStatus.RE_DERIVED_ON_LOAD,
                                 ("smartchem.service:CompilationResponse._check_receipt_bounds",))
    with _patch_item(ledger.TRANSPORT_LEDGER["Section81ReceiptView"], "stop_reason", relabel):
        flagged = unforged() == {"Section81ReceiptView.stop_reason"}
    bad = loaded is not None and flagged
    return honest, bad


# -- X-high D29 (Wave C6 closure audit C6-F8, C6-NEW-1, C6-test): one mutant per law leg -----------------------------------

_D29_CACHE: dict = {}


def _d29(name: str):
    """The honest compilations the D29 forgeries start from (cached; built OUTSIDE any patch context)."""
    if name not in _D29_CACHE:
        builders = {
            # paracetamol from the anhydride: the corpus record whose acetic-acid byproduct reads a sourced waste block
            "para": lambda: build_recompile_request("smiles:CC(=O)Nc1ccc(O)cc1", max_depth=1,
                                                    helper_reagents=("acetic acid", "water"),
                                                    stock_materials=("4-aminophenol", "acetic anhydride"),
                                                    capability_profile="poor-man"),
            # a stereo target: its IR carries a section-5.3 identity loss
            "stereo": lambda: build_recompile_request("smiles:C[C@H](O)C(=O)OC", max_depth=1, helper_reagents=("water",),
                                                      stock_materials=("methanol",)),
        }
        _D29_CACHE[name] = run_compilation(builders[name]())
    return _D29_CACHE[name]


def _byproduct_isomer_payload(resp, smiles: str = "COC=O"):
    """The Wave C6 C6-F8 forger: the corpus step's acetic-acid byproduct swapped for a same-formula isomer (the equation
    renders byte-identically), its envelope re-looked-up, everything else re-derived with the producer's own helpers.
    Returns the payload and the honest / forged dossiers."""
    from smartchem.compilation_ir import CANDIDATE_SUMMARY_SCHEMA, CandidateSummary

    req, ir = resp.request, resp.compilation_ir
    replayed = [svc._reconstruct_route(d.replay_payload) for d in resp.ranked_route_dossiers]
    k = next(i for i, r in enumerate(replayed) if r.steps[0].envelope != ConditionEnvelope.unknown()
             and any(m.formula == {"C": 2, "H": 4, "O": 2} for m in r.steps[0].products))
    step = replayed[k].steps[0]
    target = svc._structure_ident(step.target)
    products = tuple(parse_smiles(smiles).canonical() if svc._structure_ident(m) != target else m for m in step.products)
    step = dc.replace(step, products=products)
    step = dc.replace(step, envelope=rt._conditions_for(svc._ReplayedTransform(step)))
    replayed[k] = ExperimentRoute(ROUTE_SCHEMA, (step,) + replayed[k].steps[1:])
    ranked = svc._ranked_summaries(tuple(replayed), req.constraints.bounds, resp.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    cands = tuple(sorted((CandidateSummary(CANDIDATE_SUMMARY_SCHEMA, "ROUTE", r.route_digest, r.equation,
                                           "FORMAL_CANDIDATE") for r in ranked), key=lambda c: c.candidate_digest))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked), process=req.constraints.process)
    payload = response_to_payload(_forge(
        resp, ranked_route_dossiers=ranked, affordability_frontier=svc._route_frontier(req, tuple(replayed), ranked),
        compilation_ir=dc.replace(ir, candidates=cands,
                                  search_receipt=dc.replace(ir.search_receipt, results_returned=len(cands))),
        diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,))))
    new = next(r for r in ranked if r.route_digest == replayed[k].digest)
    return payload, resp.ranked_route_dossiers[k], new


@mutant("M212", "a replayed step bound by FORMULA, not structure: a byproduct isomer erases a sourced waste block "
        "(D29.1 C6-F8)", "service.CompilationResponse._check_replay_step_transforms (step shape as STRUCTURES)")
def m212():
    """Honest: paracetamol's anhydride step with its acetic-acid byproduct swapped for methyl formate (equation
    byte-identical, the whole answer re-derived) is REFUSED under verified admission. Mutant: the step shape compared by
    COMPOSITION -- exactly what the rendered equation (D26.1) could see -> it loads and the sourced waste block reads
    UNKNOWN (adf06ae's C6-F8)."""
    resp = _d29("para")
    payload, old, new = _byproduct_isomer_payload(resp)
    assert new.equation == old.equation
    _l, err = _try_load(payload, require_verified_admission=True)
    honest = err is not None and "D29.1" in err
    bad_chk = _src_mutant(CompilationResponse._check_replay_step_transforms, (
        "from .experiment.step import _ident", "_ident = lambda m: tuple(sorted(m.formula.items()))  # noqa: E731"))
    with _patch(CompilationResponse, "_check_replay_step_transforms", bad_chk):
        loaded, _err = _try_load(payload, require_verified_admission=True)
    bad = (loaded is not None and old.capability_assessment.waste.status is CapabilityStatus.BLOCKED
           and next(d for d in loaded.ranked_route_dossiers if d.route_digest == new.route_digest)
           .capability_assessment.waste.status is not CapabilityStatus.BLOCKED)
    return honest, bad


@mutant("M213", "a NEUTRAL re-centre loads on a verified-admission load (D29.1 closes the D26.4 boundary, Foreman N4)",
        "service.CompilationResponse._check_replay_step_transforms (reaction_center one the algebra assigns)")
def m213():
    resp = _d27("plain")
    formal = next(d for d in resp.ranked_route_dossiers if len(d.replay_payload) == 2)
    replay = copy.deepcopy(formal.replay_payload)
    replay[1]["reaction_center"]["n_components"] += 1
    payload = response_to_payload(dc.replace(resp, ranked_route_dossiers=tuple(
        dc.replace(d, replay_payload=replay) if d is formal else d for d in resp.ranked_route_dossiers)))
    _l, err = _try_load(payload, require_verified_admission=True)
    honest = err is not None and "re-centred replay" in err and "D29.1" in err
    bad_chk = _src_mutant(CompilationResponse._check_replay_step_transforms, (
        "if step.reaction_center not in centres:", "if False:"))
    with _patch(CompilationResponse, "_check_replay_step_transforms", bad_chk):
        loaded, _err = _try_load(payload, require_verified_admission=True)
    bad = loaded is not None
    return honest, bad


@mutant("M214", "an UNKNOWN key on a canonical capability-codec node rides the digest (D29.2 C6-NEW-1)",
        "service._check_canonical_node (exact keys per node type)")
def m214():
    resp = _d27("bench")
    wire = response_to_payload(resp)
    wire["request"]["capability_profile"]["smuggled"] = "CAPABILITY_FIT"
    _public_digest(wire, resp)
    _l, err = _try_load(wire)
    honest = err is not None and "D29.2" in err
    with _patch(svc, "_check_canonical_node", lambda node: node["type"]):     # adf06ae: ``t = node["type"]``
        loaded, _err = _try_load(wire)
    bad = loaded is not None
    return honest, bad


@mutant("M215", "an UNKNOWN key on an identity-loss entry rides the digest (D29.2 C6-NEW-1)",
        "identity.identity_loss_from_payload (exact keys)")
def m215():
    import smartchem.compilation_ir as cir_mod
    import smartchem.identity as identity_mod

    resp = _d29("stereo")
    wire = response_to_payload(resp)
    wire["compilation_ir"]["identity_losses"][0]["verified"] = True
    _public_digest(wire, resp)
    _l, err = _try_load(wire)
    honest = err is not None and "D29.2" in err
    lenient = _src_mutant(identity_mod.identity_loss_from_payload, (
        "if keys != _IDENTITY_LOSS_PAYLOAD_KEYS:", "if not keys >= _IDENTITY_LOSS_PAYLOAD_KEYS:"))
    with _patch(cir_mod, "identity_loss_from_payload", lenient):
        loaded, _err = _try_load(wire)
    bad = loaded is not None
    return honest, bad


@mutant("M216", "an UNKNOWN key on a structural candidate round-trips the IR codec (D29.2 C6-NEW-1)",
        "compilation_ir._require_exact_keys (law D29.2: the structural-candidate decoders)")
def m216():
    import smartchem.compilation_ir as cir_mod

    payload = cir_mod.ir_to_payload(cir_mod.decompile_structure_to_ir(_mol("CC"), reagents=(_mol("O"),)))
    payload["structural_candidates"][0]["verified"] = True

    def attempt():
        try:
            return cir_mod.ir_from_payload(copy.deepcopy(payload)), None
        except ValueError as exc:
            return None, str(exc)

    _ir, err = attempt()
    honest = err is not None and "D29.2" in err
    original = cir_mod._require_exact_keys
    with _patch(cir_mod, "_require_exact_keys",
                lambda p, expected, what, law="D28.5": None if law == "D29.2" else original(p, expected, what, law)):
        loaded, _err = attempt()
    bad = loaded is not None
    return honest, bad


@mutant("M217", "a ledger entry naming a check that is NOT the one refusing its forgery passes the sweep (D29.3 C6-test)",
        "tests/test_transport_ledger.py own-law lock (_OWN_LAW tag + the deepest ledger-named raising frame)")
def m217():
    """Honest: the ``standard_status`` forgery (a VALID section-8.2 name contradicting the IR) is refused BY the check
    its entry names (``_check_outcome_coherence``), in that law's own wording. Mutant: the entry relabelled to name the
    corpus check instead -- the forgery is still refused, so the pre-D29.3 sweep (which asked only "refused?") passed the
    mislabel silently; the own-law lock flags that the refusal came from a check the entry does not name."""
    import re

    import smartchem.transport_ledger as ledger

    lt = _ledger_tests()
    entry = "CompilationResponse.standard_status"
    table, _, field = entry.rpartition(".")
    _world, edit = lt._FORGERIES[entry]
    wire = response_to_payload(_d27("process"), include_replay=True)

    def refusal():
        forged = copy.deepcopy(wire)
        edit(forged, {})
        try:
            lt._reforge(forged)
            response_from_payload(forged)
        except (ValueError, TypeError, KeyError) as exc:
            return exc
        return None

    def own(exc) -> bool:
        return (re.search(lt._OWN_LAW[entry], str(exc)) is not None
                and lt._refused_in(exc) in ledger.TRANSPORT_LEDGER[table][field].checks)

    exc = refusal()
    honest = exc is not None and own(exc)
    relabel = dc.replace(ledger.TRANSPORT_LEDGER[table][field],
                         checks=("smartchem.service:CompilationResponse._check_corpus_evidence_coherence",))
    with _patch_item(ledger.TRANSPORT_LEDGER[table], field, relabel):
        exc = refusal()
        bad = exc is not None and not own(exc)
    return honest, bad


# =================================================================================================================
# runner
# =================================================================================================================

def run() -> dict:
    results = []
    only = {m.strip() for m in os.environ.get("SMARTCHEM_MUT_ONLY", "").split(",") if m.strip()}
    for mid, title, target, fn in _MUTANTS:
        if only and mid not in only:
            continue
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
