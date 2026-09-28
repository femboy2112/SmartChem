"""V0.9-MUTATION-01: the calibrated mutation gate for the capability compiler (M1-M38).

**Existence is pain, and so is a mutant that lies about being dead!** Same discipline as
`v0_8_mutation_calibration.py`: adding a test is not enough -- a test that would still pass on a BROKEN
capability compiler proves nothing. This harness injects each of the 38 failure modes the Round-II
(`docs/research/V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md`, M1-M22) and Round-III
(`docs/research/V0_9_CAPABILITY_COMPILER_ROUND_III_FREEZE_2026-09-28.md`, M23-M38) mutation-gate mappings
name, on the REAL `smartchem.capability.*` package (plus, where the failure mode lives one layer over, the
real `smartchem.experiment.stock` / `smartchem.service`), and shows the corresponding guard actually flips
(the mutant is KILLED). Every mutation is applied via a context-managed monkeypatch (or a
`dataclasses.replace`d LOCAL copy of an input) and undone on exit -- this harness never edits a single byte
of `smartchem/`, it only pokes at it in memory for the duration of one check.

Real talk up front: a handful of these mutants (M7/M8/M36) probe a NEGATIVE property -- "capability profile
selection has NO wire into the search executor at all" -- so there is no real function to sever; the only
honest way to demonstrate that absence is load-bearing is to mutate the ONE governing pin the codebase's own
noninterference tests key on (`CompilationRequest.semantic_digest`, documented as THE alias-independent
search identity) and show candidate/receipt/search-identity equality would break if that pin ever absorbed
profile content. That is still a real, non-vacuous discriminator on real production objects -- it is just
aimed at the definition of search identity rather than a severable helper.

Run:  .venv/bin/python experiments/v0_9_mutation_calibration.py
"""
from __future__ import annotations

import contextlib
import dataclasses as dc
import sys

import smartchem.capability.assess  # noqa: F401 -- imported for its side effect (populates sys.modules)
import smartchem.capability.equipment_resolver as equipment_resolver_mod
import smartchem.capability.presets as presets_mod
import smartchem.capability.requirements as requirements_mod
import smartchem.experiment.stock as stock_mod
import smartchem.service as svc
from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import AxisResult, assess
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MEASUREMENT_TIER_OF,
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
from smartchem.capability.requirements import (
    MaterialRequirement,
    RouteCapabilityRequirements,
    WasteRequirement,
    compile_capability_requirements,
)
from smartchem.constraints import PhysicalBounds
from smartchem.contracts import canonical_digest
from smartchem.data import material_library
from smartchem.data.reagents import Availability, commodity_for
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.handling import CareLevel
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
from smartchem.experiment.step import ExperimentRoute
from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    stock_material_from_commodity,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.procedure_evidence import EvidenceField
from smartchem.process_constraints import ProcessBounds
from smartchem.service import (
    CompilationRequest,
    CompilationResponse,
    build_recompile_request,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.structure import structure_by_name

# `smartchem/capability/__init__.py` does `from .assess import ..., assess`, which REBINDS the package's own
# `assess` attribute from the submodule to the FUNCTION -- so `import smartchem.capability.assess as X` would
# silently hand back a function, not the module (a real Python import-shadowing gotcha, not a smartchem bug).
# Reading it straight out of `sys.modules` sidesteps the shadowed package attribute entirely. Ooh, sneaky!
assess_mod = sys.modules["smartchem.capability.assess"]

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

_MUTANTS: list = []


def mutant(name: str):
    def deco(fn):
        _MUTANTS.append((name, fn))
        return fn
    return deco


class Vacuous(Exception):
    """Raised by a mutant body to report an honest VACUOUS/UNVERIFIED verdict, never a fabricated kill."""


@contextlib.contextmanager
def _patch(obj, name, value):
    """Temporarily set ``obj.name = value`` (works on modules and class objects), restoring exactly on exit."""
    had = name in getattr(obj, "__dict__", {})
    old = obj.__dict__.get(name) if had else None
    setattr(obj, name, value)
    try:
        yield
    finally:
        if had:
            setattr(obj, name, old)
        else:
            try:
                delattr(obj, name)
            except AttributeError:
                pass


# =================================================================================================================
# shared plumbing
# =================================================================================================================

def _search(target_name, reagents, have, max_depth, tkind=InputKind.NAME):
    target = resolve_target(target_name, tkind).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_route():
    """The real, LibreTexts-sourced, PROCESS_SPECIFIED isopentyl-acetate route -- the SAME fixture
    `tests/test_v0_9_capability_fit_positive.py` / `tests/test_v0_9_capability_round_iii.py` use."""
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return route
    raise AssertionError("expected a searched isopentyl-acetate route carrying procedure evidence")


def _molecule(name: str):
    return structure_by_name(name).molecule


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


def _readiness_at(tier: str) -> RouteReadiness:
    """A single-step RouteReadiness pinned at exactly `tier` -- the honest hand-built ladder rung, never a
    guess (a real `step.tier` assertion self-checks the fixture matches the tier it claims)."""
    S, U, UK = ObligationStatus.SATISFIED, ObligationStatus.UNSATISFIED, ObligationStatus.UNKNOWN
    if tier == FORMAL_CANDIDATE:
        step = StepReadiness(
            formal_candidate=S, reaction_type=U, reaction_class_name=None, conditions=UK, process=UK,
            workup_isolation=UK, provenance=(), open_obligations=("reaction_type: not recognized",),
        )
    elif tier == REACTION_VOUCHED:
        step = StepReadiness(
            formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=U, process=UK,
            workup_isolation=UK, provenance=(), open_obligations=("conditions: not sourced",),
        )
    elif tier == CONDITIONS_SUPPORTED:
        step = StepReadiness(
            formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=S, process=U,
            workup_isolation=UK, provenance=("https://example.test/x",), open_obligations=("process: not sourced",),
        )
    elif tier == PROCESS_SPECIFIED:
        step = StepReadiness(
            formal_candidate=S, reaction_type=S, reaction_class_name="fixture", conditions=S, process=S,
            workup_isolation=S, provenance=("https://example.test/x",), open_obligations=(),
        )
    else:
        raise ValueError(tier)
    assert step.tier == tier, (step.tier, tier)
    return RouteReadiness(per_step=(step,), route_open_obligations=step.open_obligations)


def _ps_readiness() -> RouteReadiness:
    return _readiness_at(PROCESS_SPECIFIED)


def _deglacialized_isopentyl_route() -> ExperimentRoute:
    """The real isopentyl route with the word 'glacial' stripped from its sourced procedure text (a
    `dataclasses.replace`d LOCAL copy of the SAME real `ProcedureEvidence` -- the exact "mutate the input"
    technique, not a source edit). Everything else (reaction, apparatus, catalysts) is untouched, so this is
    still an honest, sourced esterification route -- it simply no longer NAMES the glacial compendial
    formulation, which is D1's actual source-scope gate for the acetic-acid assay floor."""
    route = _isopentyl_route()
    steps = list(route.steps)
    changed = False
    for i, step in enumerate(steps):
        procedure = step.envelope.procedure
        if procedure is None or procedure.scale is None or not isinstance(procedure.scale.value, str):
            continue
        if "glacial" not in procedure.scale.value:
            continue
        new_scale = EvidenceField.present(procedure.scale.value.replace("glacial ", ""), procedure.scale.locator)
        new_ops = []
        for op in procedure.operations:
            q = op.quantity
            if q is not None and isinstance(q.value, str) and "glacial" in q.value:
                op = dc.replace(op, quantity=EvidenceField.present(q.value.replace("glacial ", ""), q.locator))
            new_ops.append(op)
        new_procedure = dc.replace(procedure, scale=new_scale, operations=tuple(new_ops))
        steps[i] = dc.replace(step, envelope=dc.replace(step.envelope, procedure=new_procedure))
        changed = True
    if not changed:
        raise AssertionError("expected 'glacial' in the real isopentyl procedure text to strip")
    return dc.replace(route, steps=tuple(steps))


def _fit_response():
    """The real, procedure-backed isopentyl route surfaced through the SERVICE under the fully-declared fit
    bench -- a genuine CAPABILITY_FIT on the shipping path (mirrors `tests/test_v0_9_capability_transport.py`)."""
    req = build_recompile_request(
        "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    return run_compilation(req)


_FAST_TARGET = "smiles:CC(=O)OC"  # methyl acetate -- a small, fast max_depth=2 search shared by M7/M8/M36


def _dual_profile_runs(profile):
    """A no-profile run and a `profile`-declared run of the SAME target, both through the real service --
    the shared plumbing M7/M8/M36 each probe a different real observable of."""
    req_none = build_recompile_request(_FAST_TARGET, max_depth=2)
    resp_none = run_compilation(req_none)
    req_prof = build_recompile_request(_FAST_TARGET, capability_profile=profile, max_depth=2)
    resp_prof = run_compilation(req_prof)
    return req_none, resp_none, req_prof, resp_prof


# =================================================================================================================
# M1-M22 (Round II)
# =================================================================================================================

@mutant("M1 commodity-lead-satisfies-material")
def m1() -> bool:
    """A commodity SOURCE LEAD is an UNKNOWN-fraction material by construction (section 10.1) -- it must
    never satisfy a pure-reagent assay requirement. Mutant: `StockMaterial.satisfies` optimistically reads
    the UPPER bound of an honestly-unknown [0,1] interval instead of the worst-case LOWER bound."""
    acetic_acid = _molecule("acetic acid")
    commodity = commodity_for(acetic_acid)
    assert commodity is not None
    stock = stock_material_from_commodity(commodity)
    requirement = MaterialRequirement(
        identity=acetic_acid, required_assay=0.99, phase=None, quantity=None,
        role="reactant", evidence_source="fixture",
    )
    profile = _profile(material_inventory=(stock,))
    real_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.UNKNOWN

    real_satisfies = stock_mod.StockMaterial.satisfies

    def mutant_satisfies(self, key, *, min_assay):
        interval = self.active_fraction_interval(key)
        if interval == (0.0, 1.0):  # BUG: an honestly-unknown commodity-lead interval optimistically satisfies
            return stock_mod.FitnessVerdict.SATISFIES
        return real_satisfies(self, key, min_assay=min_assay)

    with _patch(stock_mod.StockMaterial, "satisfies", mutant_satisfies):
        mutant_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M2 UNKNOWN-assay-sufficient")
def m2() -> bool:
    """A plain declared-present-but-unassayed stock item (not a commodity lead) never certifies FIT
    either -- the SAME [0,1]-optimistic-read mutant, applied against a DIFFERENT real fixture (a hand-built
    ethanol bottle of unknown purity, not a commodity bridge)."""
    ethanol = _molecule("ethanol")
    stock = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "stock-ethanol-unknown", "Ethanol, unspecified purity",
        (MaterialComponent.unknown_molecule(ethanol, "active"),), Phase.LIQUID, "fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, required_assay=0.9, phase=None, quantity=None, role="reactant", evidence_source="fixture",
    )
    profile = _profile(material_inventory=(stock,))
    real_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.UNKNOWN

    real_satisfies = stock_mod.StockMaterial.satisfies

    def mutant_satisfies(self, key, *, min_assay):
        interval = self.active_fraction_interval(key)
        if interval == (0.0, 1.0):  # BUG: same optimistic upper-bound read
            return stock_mod.FitnessVerdict.SATISFIES
        return real_satisfies(self, key, min_assay=min_assay)

    with _patch(stock_mod.StockMaterial, "satisfies", mutant_satisfies):
        mutant_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M3 same-formula-isomer-satisfies")
def m3() -> bool:
    """Ethanol never borrows dimethyl ether's (same formula C2H6O, different connectivity) assay -- the
    structure key is isomer-proof. Mutant: `stock._structure_key` keys on bare molecular FORMULA instead of
    the full canonical structure digest, so the two isomers collide (built INSIDE the patch, so both the
    stock's component key and the query key are computed with the SAME mutated function)."""
    ethanol = _molecule("ethanol")
    dme = _molecule("dimethyl ether")
    assert ethanol.formula == dme.formula

    def _build_and_assess():
        stock = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "stock-dme", "Dimethyl ether, pure",
            (MaterialComponent.of_molecule(dme, "active", 1.0, 1.0),), Phase.GAS, "fixture",
        )
        requirement = MaterialRequirement(
            identity=ethanol, required_assay=0.9, phase=None, quantity=None,
            role="reactant", evidence_source="fixture",
        )
        profile = _profile(material_inventory=(stock,))
        return assess(profile, _reqs(material=(requirement,)), _ps_readiness())

    real_a = _build_and_assess()
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    def mutant_structure_key(molecule):  # BUG: keys on bare formula, not full canonical structure
        return "struct:formula:" + repr(sorted(molecule.formula.items()))

    with _patch(stock_mod, "_structure_key", mutant_structure_key):
        mutant_a = _build_and_assess()
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M4 unspecified-purity=100-percent")
def m4() -> bool:
    """`required_assay=None` (the honest 'no sourced purity floor') must never be silently treated as an
    implicit 100%-satisfied requirement -- even against a perfectly pure declared bottle. Mutant: when
    `required_assay is None` and no other gate is declared, assume FIT instead of leaving it possession-only
    UNKNOWN (the exact "unspecified purity = 100%" fabrication)."""
    ethanol = _molecule("ethanol")
    stock = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "stock-ethanol-pure", "Ethanol, ACS reagent grade",
        (MaterialComponent.of_molecule(ethanol, "active", 1.0, 1.0),), Phase.LIQUID, "fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, required_assay=None, phase=None, quantity=None,
        role="reactant", evidence_source="fixture: no sourced purity spec",
    )
    profile = _profile(material_inventory=(stock,))
    real_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.UNKNOWN

    real_item = assess_mod._material_item_status_one

    def mutant_item(req, stk):
        if req.required_assay is None and req.phase is None and req.quantity is None:
            key = assess_mod._match_interval(req, stk)
            if key is not None:  # BUG: undeclared purity treated as automatically satisfied
                return CapabilityStatus.FIT, f"{stk.material_id}: BUG unspecified purity assumed 100%"
        return real_item(req, stk)

    with _patch(assess_mod, "_material_item_status_one", mutant_item):
        mutant_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M5 equipment-fuzzy-substring")
def m5() -> bool:
    """No fuzzy substring matching: a never-taught string that merely CONTAINS 'distill' must not borrow
    FRACTIONAL_DISTILLATION. Mutant: `resolve_apparatus` does substring matching on top of the exact table."""
    probe = "a distillation-adjacent gadget nobody taught this table"
    real_ok = equipment_resolver_mod.resolve_apparatus(probe) is None

    def mutant_resolve(name):
        norm = equipment_resolver_mod._normalize(name)
        hit = equipment_resolver_mod._APPARATUS_ALIASES.get(norm)
        if hit is not None:
            return hit
        if "distill" in norm:  # BUG: fuzzy substring guess
            return EquipmentCapability.FRACTIONAL_DISTILLATION
        return None

    with _patch(equipment_resolver_mod, "resolve_apparatus", mutant_resolve):
        mutant_bad = equipment_resolver_mod.resolve_apparatus(probe) is EquipmentCapability.FRACTIONAL_DISTILLATION
    return real_ok and mutant_bad


@mutant("M6 outdoors-clears-containment")
def m6() -> bool:
    """OUTDOOR ventilation never substitutes for a declared FUME_HOOD containment requirement -- a real,
    different axis. Mutant: the shared `_membership_axis` treats OUTDOOR ventilation as if it supplied the
    missing containment member, scoped to `axis=="containment"` only (so no other axis is touched)."""
    req = _reqs(containment=frozenset({ContainmentCapability.FUME_HOOD}))
    profile = _profile(containment=frozenset(), ventilation=frozenset({VentilationCapability.OUTDOOR}))
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.containment.status is CapabilityStatus.BLOCKED and real_a.overall is CapabilityStatus.BLOCKED

    real_membership = assess_mod._membership_axis

    def mutant_membership(required, available, *, axis="", extra_reasons=()):
        if axis == "containment" and VentilationCapability.OUTDOOR in profile.ventilation:
            available = available | {ContainmentCapability.FUME_HOOD}  # BUG: outdoor clears containment
        return real_membership(required, available, axis=axis, extra_reasons=extra_reasons)

    with _patch(assess_mod, "_membership_axis", mutant_membership):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.containment.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M7 profile-changes-search-candidates")
def m7() -> bool:
    """Profile selection must never move which candidate routes search returns. The real production code
    has NO wire from `capability_profile` into the search executor at all (D10: it is simply never added to
    the `semantic_digest` tuple), so the only honest way to show that absence is load-bearing is to mutate
    the ONE pin the codebase's own noninterference tests key candidate identity on."""
    _, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    req_none = resp_none.request

    def cand(resp):
        return tuple(c.candidate_digest for c in resp.compilation_ir.candidates)

    real_ok = cand(resp_none) == cand(resp_prof) and req_none.semantic_digest == req_prof.semantic_digest

    real_semantic_digest = CompilationRequest.semantic_digest

    def mutant_semantic_digest(self):
        base = real_semantic_digest.fget(self)
        if self.capability_profile is not None:  # BUG: profile content leaks into the search-identity pin
            return canonical_digest((base, self.capability_profile.profile_digest))
        return base

    with _patch(CompilationRequest, "semantic_digest", property(mutant_semantic_digest)):
        mutant_bad = req_none.semantic_digest != req_prof.semantic_digest
    return real_ok and mutant_bad


@mutant("M8 profile-changes-receipt")
def m8() -> bool:
    """The same D10 noninterference law, on the search RECEIPT specifically (not the candidate set)."""
    _, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    req_none = resp_none.request
    real_ok = (
        resp_none.compilation_ir.search_receipt.digest == resp_prof.compilation_ir.search_receipt.digest
        and req_none.semantic_digest == req_prof.semantic_digest
    )

    real_semantic_digest = CompilationRequest.semantic_digest

    def mutant_semantic_digest(self):
        base = real_semantic_digest.fget(self)
        if self.capability_profile is not None:  # BUG: profile content leaks into the search-identity pin
            return canonical_digest((base, self.capability_profile.profile_digest))
        return base

    with _patch(CompilationRequest, "semantic_digest", property(mutant_semantic_digest)):
        mutant_bad = req_none.semantic_digest != req_prof.semantic_digest
    return real_ok and mutant_bad


@mutant("M9 PROCESS_SPECIFIED-auto-FIT-skips-axis-check")
def m9() -> bool:
    """Even a PROCESS_SPECIFIED route must still have every axis checked -- tier alone must never
    short-circuit past a BLOCKED axis. Real axis evidence (from the unmodified `assess()`), fed into a
    hand-written ALTERNATIVE fold that checks tier BEFORE axes -- the fold-ORDER bug M9 names."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    assert readiness.tier == PROCESS_SPECIFIED
    real_a = assess(poor_man(), req, readiness)  # poor_man lacks distillation/IR/hood -> real BLOCKED
    real_ok = real_a.overall is CapabilityStatus.BLOCKED

    def mutant_fold(axes, tier):  # BUG: tier gate checked FIRST, short-circuiting the axis BLOCKED/UNKNOWN scan
        if tier_rank(tier) >= tier_rank(PROCESS_SPECIFIED):
            return CapabilityStatus.FIT
        if any(a.status is CapabilityStatus.BLOCKED for a in axes):
            return CapabilityStatus.BLOCKED
        if any(a.status is CapabilityStatus.UNKNOWN for a in axes):
            return CapabilityStatus.UNKNOWN
        return CapabilityStatus.FIT

    mutant_overall = mutant_fold(real_a.axes, readiness.tier)
    mutant_bad = mutant_overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M10 CONDITIONS_SUPPORTED-to-FIT")
def m10() -> bool:
    """A CONDITIONS_SUPPORTED route (strictly below PROCESS_SPECIFIED) must stay capped at UNKNOWN overall
    even when every axis is clean. Mutant: `tier_rank` is forced constant, so the HARD LAW's
    `tier_rank(tier) < tier_rank(PROCESS_SPECIFIED)` demotion check can never fire for ANY tier."""
    readiness = _readiness_at(CONDITIONS_SUPPORTED)
    real_a = assess(_profile(), _reqs(), readiness)
    real_ok = real_a.overall is CapabilityStatus.UNKNOWN

    with _patch(assess_mod, "tier_rank", lambda t: 7):  # BUG: every tier compares equal -> the floor never bites
        mutant_a = assess(_profile(), _reqs(), readiness)
    mutant_bad = mutant_a.overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M11 unrecognized-reaction-to-FIT-on-equipment")
def m11() -> bool:
    """A route whose reaction type the oracle never recognized (FORMAL_CANDIDATE only) must stay UNKNOWN
    overall no matter how well-equipped the bench -- "the equipment is fine" is never a substitute for a
    real reaction-type vouch. SAME `tier_rank`-constant mutant as M10, applied at the bottom rung."""
    readiness = _readiness_at(FORMAL_CANDIDATE)
    real_a = assess(_profile(), _reqs(), readiness)
    real_ok = real_a.overall is CapabilityStatus.UNKNOWN

    with _patch(assess_mod, "tier_rank", lambda t: 7):
        mutant_a = assess(_profile(), _reqs(), readiness)
    mutant_bad = mutant_a.overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M12 missing-verification-ignored")
def m12() -> bool:
    """A route that genuinely needs a specific analytical method (IR, per D5) and a bench that lacks it
    must BLOCK on measurement. Mutant, at the ASSESS layer (distinct from M27's requirements-layer mutant
    below): `_measurement_axis` stops comparing membership at all once no string is untabled, silently
    treating 'nothing unrecognized' as 'verification is fine'."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    real_a = assess(poor_man(), req, readiness)
    real_ok = real_a.measurement.status is CapabilityStatus.BLOCKED

    def mutant_measurement_axis(required, available, unrecognized):
        if unrecognized:
            return assess_mod._membership_axis(required, available, axis="measurement")
        return AxisResult(CapabilityStatus.FIT, ("measurement: BUG missing verification ignored",))

    with _patch(assess_mod, "_measurement_axis", mutant_measurement_axis):
        mutant_a = assess(poor_man(), req, readiness)
    mutant_bad = mutant_a.measurement.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M13 unknown-waste-passes")
def m13() -> bool:
    """A waste-routing category a profile never declared handling for must BLOCK, never silently pass.
    Mutant: the shared `_membership_axis`, scoped to `axis=="waste"`, unconditionally returns FIT."""
    req = _reqs(waste=WasteRequirement(frozenset({WasteCapability.AQUEOUS_NEUTRAL}), ("waste: fixture",)))
    profile = _profile(waste_handling=frozenset())
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.waste.status is CapabilityStatus.BLOCKED

    real_membership = assess_mod._membership_axis

    def mutant_membership(required, available, *, axis="", extra_reasons=()):
        if axis == "waste":
            return AxisResult(CapabilityStatus.FIT, ("waste: BUG unconditionally passed",) + tuple(extra_reasons))
        return real_membership(required, available, axis=axis, extra_reasons=extra_reasons)

    with _patch(assess_mod, "_membership_axis", mutant_membership):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.waste.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M14 unknown-price=0")
def m14() -> bool:
    """An unknown route cash against a declared budget must stay UNKNOWN, never a fabricated free $0.
    Mutant: `_monetary_axis` substitutes `cash=0.0` whenever both `cash`/`cash_floor` are None."""
    req = _reqs(monetary=CostVector())
    profile = _profile(budget=CostVector(cash=200.0, currency="USD", unit="USD"))
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(route_cost, budget):
        if route_cost.cash is None and route_cost.cash_floor is None:
            # BUG: unknown price assumed a free $0. Denomination-matched to the budget (USD/USD) on purpose,
            # so the fabricated zero reaches the cash compare and exposes the unknown->0 fault in ISOLATION
            # -- not incidentally tripping the D7/Wave-C-F2 fail-closed empty-denominator guard (which would
            # mask this mutant behind a denomination UNKNOWN, the reason it survived the first M1-M40 run).
            route_cost = dc.replace(route_cost, cash=0.0, currency="USD", unit="USD")
        return real_monetary(route_cost, budget)

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M15 cash-floor-within-budget=FIT")
def m15() -> bool:
    """A proven LOWER BOUND on cash that is within budget never CONFIRMS a fit (the true total could still
    be higher) -- UNKNOWN, not FIT. Mutant: `_monetary_axis` treats a floor-within-budget UNKNOWN as FIT."""
    route_cost = CostVector(cash_floor=50.0, currency="USD", unit="USD")
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    req = _reqs(monetary=route_cost)
    profile = _profile(budget=budget)
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(rc, b):
        a = real_monetary(rc, b)
        if a.status is CapabilityStatus.UNKNOWN and rc.cash is None and rc.cash_floor is not None:
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG floor-within-budget treated as FIT",))
        return a

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M16 mixed-currency-summed")
def m16() -> bool:
    """Mismatched currencies are incomparable and must never be summed/compared by raw number. Mutant:
    `_monetary_axis` compares the raw cash numbers anyway when currencies disagree."""
    route_cost = CostVector(cash=50.0, currency="USD", unit="USD")
    budget = CostVector(cash=200.0, currency="EUR", unit="USD")
    req = _reqs(monetary=route_cost)
    profile = _profile(budget=budget)
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(rc, b):
        if (
            b is not None and b.cash is not None and rc.currency and b.currency and rc.currency != b.currency
            and rc.cash is not None and rc.cash <= b.cash
        ):
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG mixed currency compared raw",))
        return real_monetary(rc, b)

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M17 unrecognized-catalyst=poor-man-obtainable")
def m17() -> bool:
    """A declared catalyst this projection could not classify (`tier is None`) BLOCKS unconditionally, no
    matter how permissive the profile. Mutant: `_procurement_axis` treats an unrecognized catalyst as
    obtainable."""
    req = _reqs(procurement_catalysts=(("a mystery catalyst nobody has named before", None),))
    profile = _profile(procurement=frozenset(Availability))
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.procurement.status is CapabilityStatus.BLOCKED

    def mutant_procurement(catalysts, allowed_tiers):
        if not catalysts:
            return AxisResult(CapabilityStatus.NOT_APPLICABLE, ("procurement: no catalyst was declared",))
        reasons = tuple(
            f"procurement: BUG unrecognized catalyst {name!r} assumed obtainable" if tier is None
            else f"procurement: {name!r} tier {tier.value!r}"
            for name, tier in catalysts
        )
        return AxisResult(CapabilityStatus.FIT, reasons)

    with _patch(assess_mod, "_procurement_axis", mutant_procurement):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.procurement.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M18 industrial-catalyst-free-under-lab")
def m18() -> bool:
    """A profile whose declared procurement tiers never reached INDUSTRIAL does not get an industrial
    catalyst for free. Mutant: `is_obtainable_under` treats ANY non-empty declared tier set as reaching
    every tier, including INDUSTRIAL."""
    req = _reqs(procurement_catalysts=(("Pd/C", Availability.INDUSTRIAL),))
    kitchen_profile = _profile(procurement=frozenset({Availability.GROCERY, Availability.HARDWARE}))
    real_a = assess(kitchen_profile, req, _ps_readiness())
    real_ok = real_a.procurement.status is CapabilityStatus.BLOCKED

    def mutant_is_obtainable_under(tier, allowed_tiers):
        return bool(allowed_tiers)  # BUG: any non-empty declared tier set obtains EVERYTHING

    with _patch(assess_mod, "is_obtainable_under", mutant_is_obtainable_under):
        mutant_a = assess(kitchen_profile, req, _ps_readiness())
    mutant_bad = mutant_a.procurement.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M19 assessment-under-another-profile-no-refusal")
def m19() -> bool:
    """A `CapabilityAssessment` computed under profile A, carried under a request declaring profile B, must
    be REFUSED on load. Mutant: `_check_capability_coherence` (the guard that catches this) is disabled."""
    resp = _fit_response()
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=poor_man()))
    real_refuses = False
    try:
        swapped._check_capability_coherence(require_verified_admission=True)
    except ValueError:
        real_refuses = True

    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            swapped._check_capability_coherence(require_verified_admission=True)
            mutant_loads = True
        except ValueError:
            mutant_loads = False
    return real_refuses and mutant_loads


@mutant("M20 custom-content-changes-digest-doesnt")
def m20() -> bool:
    """Two Custom profiles with DIFFERENT declared content must carry DIFFERENT `profile_digest`s. Mutant:
    `CapabilityProfile.profile_digest` is forced constant, so content changes stop moving the pin."""
    p1 = custom(profile_id="x1", equipment=frozenset({EquipmentCapability.BALANCE}))
    p2 = custom(profile_id="x1", equipment=frozenset({EquipmentCapability.REFLUX_CONDENSER}))
    real_ok = p1.profile_digest != p2.profile_digest

    with _patch(CapabilityProfile, "profile_digest", property(lambda self: "constant-digest-bug")):
        mutant_bad = p1.profile_digest == p2.profile_digest
    return real_ok and mutant_bad


@mutant("M21 one-operations-equipment-view-promotes-under-equipped-route")
def m21() -> bool:
    """A route's equipment requirement is the UNION over EVERY recorded operation's sourced apparatus --
    the real isopentyl procedure names a plain flask in op1 (REACTION_VESSEL) but a reflux condenser,
    separatory funnel and fractional-distillation rig only in LATER operations. A bench that covers only
    op1's flask must still BLOCK on the rest.

    The real route ALSO carries a whole-step `ProcessRequirements.equipment` cross-check tuple that happens
    to duplicate the full apparatus list on its own (decision 2's "+ ProcessRequirements.equipment cross-
    check") -- stripped here via a `dataclasses.replace`d LOCAL copy of the envelope, so the fixture isolates
    the per-OPERATION union specifically (leaving that redundant cross-check in place would mask the mutant
    below and make this an accidental pass, not a real kill).

    Mutant: `_equipment_requirement` only scans each step's FIRST recorded operation, silently dropping every
    later operation's apparatus demand -- "one [operation]'s view promotes a route that's missing what the
    REST of the sourced procedure needs"."""
    base_route = _isopentyl_route()
    steps = list(base_route.steps)
    for i, step in enumerate(steps):
        if step.envelope.process is not None and step.envelope.process.equipment:
            stripped_process = dc.replace(step.envelope.process, equipment=())
            steps[i] = dc.replace(step, envelope=dc.replace(step.envelope, process=stripped_process))
    route = dc.replace(base_route, steps=tuple(steps))

    req = compile_capability_requirements(route)
    assert EquipmentCapability.REACTION_VESSEL in req.equipment  # op1's "100-mL round-bottom flask"
    assert EquipmentCapability.REFLUX_CONDENSER in req.equipment  # a LATER operation
    assert EquipmentCapability.FRACTIONAL_DISTILLATION in req.equipment  # a LATER operation
    readiness = evaluate_route(route)
    profile = _profile(equipment=frozenset({EquipmentCapability.REACTION_VESSEL}))  # covers op1 ONLY
    real_a = assess(profile, req, readiness)
    real_ok = real_a.equipment.status is CapabilityStatus.BLOCKED

    def mutant_equipment_requirement(rt_):
        raw: "set[str]" = set()
        for step in rt_.steps:
            procedure = step.envelope.procedure
            if procedure is not None:
                for op in procedure.operations[:1]:  # BUG: only the FIRST recorded operation is scanned
                    if op.kind is not requirements_mod.OperationKind.VERIFY:
                        raw.update(op.apparatus)
            process = step.envelope.process
            if process is not None and process.equipment is not None:
                raw.update(process.equipment)
        recognized, _ignored, unrecognized = requirements_mod.classify_apparatus_strings(raw)
        return recognized, tuple(sorted(unrecognized))

    with _patch(requirements_mod, "_equipment_requirement", mutant_equipment_requirement):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(profile, req2, readiness)
    mutant_bad = mutant_a.equipment.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M22 FIT-survives-readiness-demotion")
def m22() -> bool:
    """The SAME axes-clean route+bench must un-FIT the moment its readiness is (honestly) demoted below
    PROCESS_SPECIFIED. Real: PROCESS_SPECIFIED -> FIT, REACTION_VOUCHED -> UNKNOWN. Mutant: the M9/M10 tier-
    shortcircuit fold, applied to the DEMOTED case's real axis evidence, lets FIT survive the demotion."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    bench = isopentyl_capability_fit_bench()
    real_full = assess(bench, req, evaluate_route(route))
    demoted_readiness = _readiness_at(REACTION_VOUCHED)
    real_demoted = assess(bench, req, demoted_readiness)
    real_ok = real_full.overall is CapabilityStatus.FIT and real_demoted.overall is CapabilityStatus.UNKNOWN

    def mutant_fold(axes, tier):  # the SAME tier-shortcircuit bug as M9
        if tier_rank(tier) >= tier_rank(PROCESS_SPECIFIED):
            return CapabilityStatus.FIT
        if any(a.status is CapabilityStatus.BLOCKED for a in axes):
            return CapabilityStatus.BLOCKED
        if any(a.status is CapabilityStatus.UNKNOWN for a in axes):
            return CapabilityStatus.UNKNOWN
        return CapabilityStatus.FIT

    mutant_overall = mutant_fold(real_demoted.axes, demoted_readiness.tier)
    mutant_bad = mutant_overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


# =================================================================================================================
# M23-M38 (Round III)
# =================================================================================================================

@mutant("M23 reaction-class-label-manufactures-universal-assay-floor")
def m23() -> bool:
    """The retired universal esterification floor stays dead: a de-glacialized (but still real, sourced,
    still-esterification) isopentyl route earns NO assay floor on its acetic-acid leaf. Mutant:
    `_material_requirements` reintroduces the RETIRED class-scoped floor (assay=0.98 for ANY acetic-acid
    leaf, no source-text gate)."""
    route = _deglacialized_isopentyl_route()
    ids = requirements_mod._known_leaf_ids()
    req = compile_capability_requirements(route)
    acetic_req = next(
        (m_ for m_ in req.material if m_.identity is not None
         and requirements_mod._struct_digest(m_.identity) == ids["acetic_acid"]), None,
    )
    real_ok = acetic_req is not None and acetic_req.required_assay is None

    def mutant_material_requirements(rt_):
        out = []
        for leaf in rt_.leaf_inputs:
            digest = requirements_mod._struct_digest(leaf)
            if digest == ids["acetic_acid"]:  # BUG: universal class-scoped floor, no source-text gate
                out.append(MaterialRequirement(
                    identity=leaf, required_assay=0.98, phase=None, quantity=None,
                    role="reactant (BUG universal floor)", evidence_source="mutant: class-scoped floor",
                ))
            else:
                out.append(MaterialRequirement(
                    identity=leaf, required_assay=None, phase=None, quantity=None,
                    role="reactant", evidence_source="mutant",
                ))
        out.extend(requirements_mod._procedure_only_material_requirements(rt_))
        return tuple(out)

    with _patch(requirements_mod, "_material_requirements", mutant_material_requirements):
        req2 = compile_capability_requirements(route)
    mutant_req = next(
        (m_ for m_ in req2.material if m_.identity is not None
         and requirements_mod._struct_digest(m_.identity) == ids["acetic_acid"]), None,
    )
    mutant_bad = mutant_req is not None and mutant_req.required_assay == 0.98
    return real_ok and mutant_bad


@mutant("M24 procedure-only-consumables-vanish-from-material")
def m24() -> bool:
    """Procedure-only auxiliaries (H2SO4 catalyst, NaHCO3/NaCl/MgSO4 washes+drier, water) must PARTICIPATE
    in the material axis -- a two-bottle bench (reagents only) BLOCKS on the missing magnesium sulfate.
    Mutant: `_procedure_only_material_requirements` returns nothing, silently dropping every auxiliary."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    profile = research_lab(material_inventory=material_library.isopentyl_lab_inventory())
    real_a = assess(profile, req, readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED
    assert "magnesium sulfate" in " ".join(real_a.material.reasons)

    with _patch(requirements_mod, "_procedure_only_material_requirements", lambda rt_: ()):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(profile, req2, readiness)
    # the auxiliary-driven BLOCK must vanish entirely (silently dropped -> never still a provable negative)
    mutant_bad = mutant_a.material.status is not CapabilityStatus.BLOCKED
    return real_ok and mutant_bad


@mutant("M25 required-quantity-ignored")
def m25() -> bool:
    """A bench stocking too LITTLE of a quantity-gated reactant (10 mL glacial vs the sourced 20 mL draw)
    BLOCKS on quantity. Mutant: `_material_item_status_one` strips the quantity gate, scoped to the
    glacial-acetic-acid requirement ONLY (every other requirement -- including the water/wash items that are
    themselves only FIT because their OWN quantity gate passes -- must stay untouched, or stripping quantity
    everywhere would just trade one BLOCKED item for a different UNKNOWN one and the mutant would survive
    for the wrong reason)."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    profile = isopentyl_capability_fit_bench(
        material_inventory=material_library.isopentyl_insufficient_quantity_inventory(),
    )
    real_a = assess(profile, req, readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    real_item = assess_mod._material_item_status_one
    acetic_acid_digest = requirements_mod._known_leaf_ids()["acetic_acid"]

    def mutant_item(requirement, stock):
        if (
            requirement.quantity is not None and requirement.identity is not None
            and requirements_mod._struct_digest(requirement.identity) == acetic_acid_digest
        ):
            requirement = dc.replace(requirement, quantity=None)  # BUG: quantity gate silently dropped
        return real_item(requirement, stock)

    with _patch(assess_mod, "_material_item_status_one", mutant_item):
        mutant_a = assess(profile, req, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M26 known-phase-mismatch-still-FITs")
def m26() -> bool:
    """A mis-phased alcohol bottle (dilute AQUEOUS vs the required neat LIQUID) BLOCKS on phase. Mutant:
    `_material_item_status_one` strips the phase gate, scoped to the isoamyl-alcohol requirement ONLY (the
    same "don't trade one BLOCKED for a different UNKNOWN elsewhere" discipline as M25)."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    profile = isopentyl_capability_fit_bench(material_inventory=material_library.isopentyl_wrong_phase_inventory())
    real_a = assess(profile, req, readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    real_item = assess_mod._material_item_status_one
    isoamyl_digest = requirements_mod._known_leaf_ids()["isoamyl"]

    def mutant_item(requirement, stock):
        if (
            requirement.phase is not None and requirement.identity is not None
            and requirements_mod._struct_digest(requirement.identity) == isoamyl_digest
        ):
            requirement = dc.replace(requirement, phase=None)  # BUG: phase gate silently dropped
        return real_item(requirement, stock)

    with _patch(assess_mod, "_material_item_status_one", mutant_item):
        mutant_a = assess(profile, req, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M27 required-analytical-method-ignored")
def m27() -> bool:
    """The real isopentyl route's IR requirement BLOCKS a poor_man bench that lacks IR. Mutant (at the
    REQUIREMENTS layer, distinct from M12's assess-layer mutant): `_measurement_requirement` derives NO
    measurement requirement at all -- the demand vanishes upstream."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    real_a = assess(poor_man(), req, readiness)
    real_ok = real_a.measurement.status is CapabilityStatus.BLOCKED

    with _patch(requirements_mod, "_measurement_requirement", lambda rt_: (frozenset(), ())):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(poor_man(), req2, readiness)
    mutant_bad = mutant_a.measurement.status is not CapabilityStatus.BLOCKED
    return real_ok and mutant_bad


@mutant("M28 generic-ANALYTICAL_INSTRUMENT-substitutes-for-specific-method")
def m28() -> bool:
    """A profile owning MELTING_POINT does not clear a MASS requirement just because both share the
    CHEAP_INSTRUMENT tier -- comparison must be on the SPECIFIC method. Mutant: `_measurement_axis` compares
    on the coarse `MEASUREMENT_TIER_OF` tier instead."""
    req = _reqs(measurement=frozenset({MeasurementMethod.MASS}))
    profile = _profile(measurement=frozenset({MeasurementMethod.MELTING_POINT}))
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.measurement.status is CapabilityStatus.BLOCKED

    def mutant_measurement_axis(required, available, unrecognized):
        if unrecognized:
            return assess_mod._membership_axis(required, available, axis="measurement")
        req_tiers = {MEASUREMENT_TIER_OF[m_] for m_ in required}
        avail_tiers = {MEASUREMENT_TIER_OF[m_] for m_ in available}
        if req_tiers <= avail_tiers:  # BUG: tier-only comparison, never the specific method
            return AxisResult(CapabilityStatus.FIT, ("measurement: BUG tier-only comparison",))
        return AxisResult(CapabilityStatus.BLOCKED, ("measurement: tier missing",))

    with _patch(assess_mod, "_measurement_axis", mutant_measurement_axis):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.measurement.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M29 UNCONSTRAINED-with-real-demand-silently-FITs")
def m29() -> bool:
    """A route with a real 416.15 K demand against a profile declaring NO ceiling must be UNKNOWN, never a
    free UNCONSTRAINED pass. Mutant: `_physical_axis` reverts to the retired Round-II rule (no ceiling
    always means UNCONSTRAINED, regardless of the route's own demand)."""
    req = _reqs(physical=PhysicalBounds.of(max_temperature_k=416.15))
    profile = _profile()
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.physical.status is CapabilityStatus.UNKNOWN and real_a.overall is CapabilityStatus.UNKNOWN

    real_physical_axis = assess_mod._physical_axis

    def mutant_physical_axis(requirement, ceiling):
        if not ceiling.constrains_anything:  # BUG: ignores whether the ROUTE itself has a real demand
            return AxisResult(CapabilityStatus.UNCONSTRAINED, ("physical: BUG unconstrained regardless of demand",))
        return real_physical_axis(requirement, ceiling)

    with _patch(assess_mod, "_physical_axis", mutant_physical_axis):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M30 budget-compares-different-CostVector-units")
def m30() -> bool:
    """A per-metric-ton route cost vs a total-USD budget is a denomination mismatch -> UNKNOWN, never
    compared by raw number. Mutant: `_monetary_axis` ignores the unit mismatch."""
    route_cost = CostVector(cash=5.0, currency="USD", unit="metric ton")
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    req = _reqs(monetary=route_cost)
    profile = _profile(budget=budget)
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(rc, b):
        if (
            b is not None and b.cash is not None and rc.unit and b.unit and rc.unit != b.unit
            and rc.cash is not None and rc.cash <= b.cash
        ):
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG unit mismatch compared raw",))
        return real_monetary(rc, b)

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M31 per-mol-cost-compared-to-total-budget")
def m31() -> bool:
    """The twin M30 scenario with a DIFFERENT denomination (per-mol-product cost vs a total-USD budget, no
    production-quantity bridge) -- same guard, a second real denomination pairing."""
    route_cost = CostVector(cash=3.0, currency="USD", unit="mol-product")
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    req = _reqs(monetary=route_cost)
    profile = _profile(budget=budget)
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(rc, b):
        if (
            b is not None and b.cash is not None and rc.unit and b.unit and rc.unit != b.unit
            and rc.cash is not None and rc.cash <= b.cash
        ):
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG unit mismatch compared raw",))
        return real_monetary(rc, b)

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M32 ventilation-silently-claims-an-assessed-axis")
def m32() -> bool:
    """Ventilation is an explicit RESERVED axis (D8) -- surfaced, never a silent green check. Mutant:
    `_ventilation_axis` returns a bare FIT with no RESERVED note, hiding that the axis is unassessed."""
    real_a = assess(_profile(), _reqs(), _ps_readiness())
    real_ok = (
        real_a.ventilation.status is CapabilityStatus.NOT_APPLICABLE
        and "RESERVED" in " ".join(real_a.ventilation.reasons)
    )

    def mutant_ventilation_axis():
        return AxisResult(CapabilityStatus.FIT, ("ventilation: BUG assessed, no reserved note",))

    with _patch(assess_mod, "_ventilation_axis", mutant_ventilation_axis):
        mutant_a = assess(_profile(), _reqs(), _ps_readiness())
    mutant_bad = (
        mutant_a.ventilation.status is CapabilityStatus.FIT
        and "RESERVED" not in " ".join(mutant_a.ventilation.reasons)
    )
    return real_ok and mutant_bad


@mutant("M33 procedure-only-hazardous-material-omitted-from-containment")
def m33() -> bool:
    """The isopentyl route's H2SO4 catalyst (procedure-only, resolvable, H314) NAMES itself in the
    containment requirement's reasons, and the unresolvable washes/drier are surfaced in `hazard_unresolved`
    -- 'inform, never neuter' (D9). On THIS corpus route the balanced lane (acetic acid's own hazard)
    independently already forces the FUME_HOOD member, so the containment SET is not the observable that
    moves; the NAMED evidence is. Mutant: `_procedure_hazard_scan` always reports no forced containment and
    no unresolved hazards -- the H2SO4/H314 justification and every unresolved-hazard note silently vanish,
    even though (on this route) the hood requirement itself survives via the redundant balanced-lane path."""
    route = _isopentyl_route()
    req = compile_capability_requirements(route)
    real_ok = (
        req.containment == frozenset({ContainmentCapability.FUME_HOOD})
        and "sulfuric acid" in " ".join(req.containment_reasons)
        and "H314" in " ".join(req.containment_reasons)
        and any("sodium bicarbonate" in r for r in req.hazard_unresolved)
    )

    with _patch(requirements_mod, "_procedure_hazard_scan", lambda rt_: (False, (), ())):
        req2 = compile_capability_requirements(route)
    mutant_bad = req2.containment_reasons == () and req2.hazard_unresolved == ()

    # non-vacuous downstream consequence: assess()'s containment axis reasons carry the SAME omission --
    # a caller reading the assessed reasons (not just the requirement) also loses the H2SO4/H314 evidence.
    readiness = evaluate_route(route)
    real_fit = assess(isopentyl_capability_fit_bench(), req, readiness)
    mutant_fit = assess(isopentyl_capability_fit_bench(), req2, readiness)
    consequence_ok = (
        "sulfuric acid" in " ".join(real_fit.containment.reasons)
        and "sulfuric acid" not in " ".join(mutant_fit.containment.reasons)
    )
    return real_ok and mutant_bad and consequence_ok


@mutant("M34 named-preset-request-stores-only-the-name")
def m34() -> bool:
    """A request built from a preset NAME stores the RESOLVED snapshot (D10), immune to a later mutation of
    the preset table. Mutant (counterfactual, no source edit): a hypothetical 'stores only the name, re-
    resolves at replay time' implementation is simulated by calling `resolve_capability_profile` on the
    request's own carried `capability_profile_origin` AFTER the preset table is mutated -- showing that path
    would drift, while the real stored snapshot does not."""
    req = build_recompile_request(_FAST_TARGET, capability_profile="poor-man", max_depth=2)
    original_snapshot = req.capability_profile
    assert original_snapshot is not None and req.capability_profile_origin == "poor-man"

    different_poor_man = custom(profile_id="poor-man", equipment=frozenset({EquipmentCapability.BALANCE}))
    assert different_poor_man != original_snapshot
    mutated_presets = dict(presets_mod.CAPABILITY_PROFILE_PRESETS)
    mutated_presets["poor-man"] = lambda: different_poor_man

    with _patch(presets_mod, "CAPABILITY_PROFILE_PRESETS", mutated_presets):
        # real: the ALREADY-BUILT request's stored snapshot is unaffected by tomorrow's mutated preset table
        real_ok = req.capability_profile == original_snapshot
        # mutant model: a "stores only the name, re-resolve on replay" implementation drifts
        reresolved = resolve_capability_profile(req.capability_profile_origin)
        mutant_bad = reresolved != original_snapshot
    return real_ok and mutant_bad


@mutant("M35 custom-content-changes-without-capability_question_digest-moving")
def m35() -> bool:
    """Two requests with DIFFERENT declared custom-profile content (same search question) must carry
    DIFFERENT `capability_question_digest`s. Mutant: the property drops the profile leg of the pin."""
    p1 = custom(profile_id="a", equipment=frozenset({EquipmentCapability.BALANCE}))
    p2 = custom(profile_id="a", equipment=frozenset({EquipmentCapability.REFLUX_CONDENSER}))
    r1 = build_recompile_request(_FAST_TARGET, capability_profile=p1, max_depth=2)
    r2 = build_recompile_request(_FAST_TARGET, capability_profile=p2, max_depth=2)
    real_ok = (
        r1.capability_question_digest != r2.capability_question_digest and r1.semantic_digest == r2.semantic_digest
    )

    def mutant_cqd(self):
        if self.capability_profile is None:  # BUG: profile content dropped from the pin entirely
            return None
        return self.semantic_digest

    with _patch(CompilationRequest, "capability_question_digest", property(mutant_cqd)):
        mutant_bad = r1.capability_question_digest == r2.capability_question_digest
    return real_ok and mutant_bad


@mutant("M36 profile-selection-changes-search-question-identity")
def m36() -> bool:
    """The full-request law: `semantic_digest` (the alias-independent SEARCH identity) must not move under a
    profile change. Real: two full service runs {no profile, poor-man} on the same target share one
    `semantic_digest`. Mutant: the governing pin absorbs profile content."""
    req_none, resp_none, req_prof, resp_prof = _dual_profile_runs("poor-man")
    real_ok = (
        req_none.semantic_digest == req_prof.semantic_digest
        and resp_none.search_space_status == resp_prof.search_space_status
    )

    real_semantic_digest = CompilationRequest.semantic_digest

    def mutant_semantic_digest(self):
        base = real_semantic_digest.fget(self)
        if self.capability_profile is not None:  # BUG: profile selection changes the search-question pin
            return canonical_digest((base, self.capability_profile.profile_digest))
        return base

    with _patch(CompilationRequest, "semantic_digest", property(mutant_semantic_digest)):
        mutant_bad = req_none.semantic_digest != req_prof.semantic_digest
    return real_ok and mutant_bad


@mutant("M37 no-profile-request-silently-receives-a-bench-assumption")
def m37() -> bool:
    """A NOT_REQUESTED (no-profile) request must carry `capability_assessment is None` on every dossier.
    Real: an honest no-profile run does. Then: a FORGED assessment smuggled onto a NOT_REQUESTED response is
    refused by `_check_capability_coherence`. Mutant: that guard is disabled."""
    req_none, resp_none, _, resp_prof = _dual_profile_runs("poor-man")
    real_ok = all(d.capability_assessment is None for d in resp_none.ranked_route_dossiers)

    forged_assessment = next(
        d.capability_assessment for d in resp_prof.ranked_route_dossiers if d.capability_assessment is not None
    )
    dossiers = list(resp_none.ranked_route_dossiers)
    dossiers[0] = dc.replace(dossiers[0], capability_assessment=forged_assessment)
    forged_resp = dc.replace(resp_none, ranked_route_dossiers=tuple(dossiers))

    real_refuses = False
    try:
        forged_resp._check_capability_coherence(require_verified_admission=True)
    except ValueError:
        real_refuses = True

    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            forged_resp._check_capability_coherence(require_verified_admission=True)
            mutant_loads = True
        except ValueError:
            mutant_loads = False
    return real_ok and real_refuses and mutant_loads


@mutant("M38 canonical-CAPABILITY_FIT-loads-after-evidence-altered")
def m38() -> bool:
    """A genuine canonical CAPABILITY_FIT wire payload whose carried profile snapshot is tampered (declared
    stock stripped) must be REFUSED on load -- the carried FIT no longer re-derives. The pin
    (`capability_question_digest`) is forged CONSISTENTLY with the tampered profile first (a stale pin would
    catch the tamper on its own, which is a DIFFERENT, shallower guard than CAPABILITY-REBIND-ON-LOAD and
    would make the mutant below vacuous) -- so the only thing left standing between this forged wire and a
    successful load is the re-derivation guard itself. Mutant: that guard is disabled, and the forged wire
    loads with the fabricated FIT intact."""
    resp = _fit_response()
    assert any(
        d.capability_assessment and d.capability_assessment.overall is CapabilityStatus.FIT
        for d in resp.ranked_route_dossiers
    )
    payload = response_to_payload(resp)  # include_replay=True default -> CANONICAL_VERIFIED
    cp = payload["request"]["capability_profile"]
    for f in cp["fields"]:
        if f[0] == "material_inventory":
            f[1]["items"] = []  # strip the declared stock the FIT depended on
    tampered_profile = svc._capability_profile_from_payload(cp)
    payload["capability_question_digest"] = canonical_digest(
        (resp.request.semantic_digest, tampered_profile.profile_digest),
    )  # forge the pin consistently -- isolate the REBIND guard specifically

    real_refuses = False
    try:
        response_from_payload(payload)
    except ValueError:
        real_refuses = True

    with _patch(CompilationResponse, "_check_capability_coherence", lambda self, **kw: None):
        try:
            back = response_from_payload(payload)
            mutant_loads = any(
                d.capability_assessment and d.capability_assessment.overall is CapabilityStatus.FIT
                for d in back.ranked_route_dossiers
            )
        except ValueError:
            mutant_loads = False
    return real_refuses and mutant_loads


@mutant("M39 partial-physical-ceiling-drops-an-undeclared-but-demanded-dimension")
def m39() -> bool:
    """Wave-C F1 (evil-morty directed + dalembert structure-theorem, both proved it): D6's all-None guard
    fired ONLY when the ceiling constrained NOTHING. A profile that constrains ONE physical dimension and
    leaves another ``None``, against a route demanding the unconstrained dimension, silently dropped that
    demand and rode to FIT (a temp-only bench certified for a real 100 atm demand it never bounded). The
    fix applies D6 PER DIMENSION. Mutant: `_physical_axis` checks only the CEILING's declared dimensions
    (the pre-fix behavior), dropping the route-demanded-but-unbounded dimension.

    This is the discriminator M29 was too weak to be -- M29 only exercised the all-None ceiling, which the
    code always handled; the hole lived in the partial-ceiling case, uncaught until the fresh hostile review.
    """
    req = _reqs(physical=PhysicalBounds.of(max_pressure_atm=100.0))                 # a real 100 atm demand
    profile = _profile(physical_bounds=PhysicalBounds.of(max_temperature_k=500.0))  # temp-only, NO pressure
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.physical.status is CapabilityStatus.UNKNOWN

    def mutant_physical_axis(requirement, ceiling):
        # BUG (pre-Wave-C): iterate only the dimensions the CEILING declares; a route demand on a dimension
        # whose ceiling is None is never entered -> silently dropped -> the axis returns FIT.
        if not ceiling.constrains_anything:
            return AxisResult(CapabilityStatus.UNKNOWN, ("physical: all-None handled by D6 (unchanged)",))
        blocked = False
        for demand, ceil, is_floor in (
            (requirement.max_temperature_k, ceiling.max_temperature_k, False),
            (requirement.max_pressure_atm, ceiling.max_pressure_atm, False),
            (requirement.min_pressure_atm, ceiling.min_pressure_atm, True),
        ):
            if ceil is not None and demand is not None and (demand < ceil if is_floor else demand > ceil):
                blocked = True
        return AxisResult(
            CapabilityStatus.BLOCKED if blocked else CapabilityStatus.FIT,
            ("physical: BUG only ceiling-declared dimensions checked",),
        )

    with _patch(assess_mod, "_physical_axis", mutant_physical_axis):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.physical.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M40 empty-denominator-cost-wildcards-to-FIT")
def m40() -> bool:
    """Wave-C F2 (evil-morty): the pre-fix `_monetary_axis` denomination guards (`if x and y and x != y`)
    SKIPPED on an empty string, so a cost that failed to record its currency AND unit fell through to the
    raw cash compare and FIT -- an undeclared basis treated as commensurable with any budget. The fix is
    fail-closed: to compare cash at all, BOTH sides must declare a currency AND unit, matching. Mutant: the
    old skip-on-empty guard."""
    route_cost = CostVector(cash=5.0, currency="", unit="")   # undeclared denomination, known cash
    budget = CostVector(cash=200.0, currency="USD", unit="USD")
    req = _reqs(monetary=route_cost)
    profile = _profile(budget=budget)
    real_a = assess(profile, req, _ps_readiness())
    real_ok = real_a.monetary.status is CapabilityStatus.UNKNOWN

    real_monetary = assess_mod._monetary_axis

    def mutant_monetary(rc, b):
        if b is None or b.cash is None or (rc.cash is None and rc.cash_floor is None):
            return real_monetary(rc, b)
        # BUG: skip-on-empty guards (pre-fix) -> an empty denominator never blocks -> raw compare -> FIT
        if rc.currency and b.currency and rc.currency != b.currency:
            return real_monetary(rc, b)
        if rc.unit and b.unit and rc.unit != b.unit:
            return real_monetary(rc, b)
        if rc.cash is not None and rc.cash <= b.cash:
            return AxisResult(CapabilityStatus.FIT, ("monetary: BUG empty-denominator wildcarded to FIT",))
        return real_monetary(rc, b)

    with _patch(assess_mod, "_monetary_axis", mutant_monetary):
        mutant_a = assess(profile, req, _ps_readiness())
    mutant_bad = mutant_a.monetary.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


def run() -> list:
    results = []
    for name, fn in _MUTANTS:
        try:
            killed = bool(fn())
            status = "KILLED" if killed else "SURVIVED"
        except Vacuous as exc:
            killed, status = None, f"VACUOUS({exc})"
        except Exception as exc:  # a harness error is a FAILED kill, reported honestly -- never a ceremonial pass
            killed, status = False, "SURVIVED"
            name = f"{name} [harness-error: {type(exc).__name__}: {exc}]"
        results.append((name, killed, status))
        print(f"  [{status}] {name}", flush=True)
    return results


def main() -> int:
    print(f"v0.9 capability compiler mutation gate (M1-M40, {len(_MUTANTS)} mutants registered):", flush=True)
    results = run()
    killed = sum(1 for _, k, _ in results if k is True)
    vacuous = sum(1 for _, k, _ in results if k is None)
    survived = sum(1 for _, k, _ in results if k is False)
    print(f"\n{killed}/{len(results)} mutants killed. {vacuous} VACUOUS. {survived} SURVIVED (real gap).")
    return 0 if survived == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
