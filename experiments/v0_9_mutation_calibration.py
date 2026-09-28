"""V0.9-MUTATION-01: the calibrated mutation gate for the capability compiler (M1-M62, RC Round IV).

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
from fractions import Fraction

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
from smartchem.conditions import Interval
from smartchem.constraints import PhysicalBounds
from smartchem.contracts import canonical_digest
from smartchem.data import material_library
from smartchem.data.derived_evidence import (
    DerivationMethod,
    DerivedIntervalEvidence,
    IntervalUnit,
    solution_fraction_from_solubility,
    symmetric_band,
)
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
    StockQuantity,
    stock_material_from_commodity,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.procedure_evidence import ProcedureMaterialRole, ProcedureMaterialUse
from smartchem.process_constraints import Attention, ProcessBounds, ProcessRequirements
from smartchem.service import (
    CompilationRequest,
    CompilationResponse,
    TransformGrammar,
    build_recompile_request,
    ranked_summary_from_payload,
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


_ISO_ROUTE_CACHE: list = []


def _isopentyl_route():
    """The real, LibreTexts-sourced, PROCESS_SPECIFIED isopentyl-acetate route -- the SAME fixture
    `tests/test_v0_9_capability_fit_positive.py` / `tests/test_v0_9_capability_round_iii.py` use. Cached across
    mutants: the search is deterministic and read-only, so re-running it per mutant only burns wall-clock (the
    Round-IV gate calls it a dozen-plus times); the cached ExperimentRoute is immutable/frozen and every mutant
    that needs a LOCAL edit takes a `dataclasses.replace`d copy, never touching this shared object."""
    if _ISO_ROUTE_CACHE:
        return _ISO_ROUTE_CACHE[0]
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                _ISO_ROUTE_CACHE.append(route)
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


def _fit_response():
    """The real, procedure-backed isopentyl route surfaced through the SERVICE under the fully-declared fit
    bench (mirrors `tests/test_v0_9_capability_transport.py`). Round IV: this is overall **UNKNOWN**, not FIT
    (process/containment/waste under-specify), but it DOES carry a real per-route CapabilityAssessment whose
    material axis rests on the declared stock -- the object the transport-guard mutants (M19/M38/M54) probe."""
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
# Round-IV shared plumbing (F41-F62): finite-pool flow mutants, wrong-formulation benches, route surgery
# =================================================================================================================

def _unlimited_pool_flow(n, edges, source, sink):
    """A finite-pool `_max_flow` reverted to the pre-F42 "stock is unlimited" behaviour: every source-side
    demand that has ANY path to the sink is counted as fully met, WITHOUT ever debiting a bottle's shared
    capacity. Faithfully reproduces the double-spend / no-capacity-ledger fault (a bottle spent as many times
    as demands reach it). Returns the SUM of source-out capacities whose demand can reach the sink."""
    adj: "dict[int, list[tuple[int, float]]]" = {}
    for u, v, c in edges:
        adj.setdefault(u, []).append((v, c))

    def _reaches(u, seen):
        if u == sink:
            return True
        for v, _ in adj.get(u, ()):  # ignore capacity: this is the "infinite bottle" bug
            if v not in seen:
                seen.add(v)
                if _reaches(v, seen):
                    return True
        return False

    return sum(c for v, c in adj.get(source, ()) if _reaches(v, {source, v}))


def _single_bottle_flow(n, edges, source, sink):
    """A `_max_flow` that FAILS to combine compatible bottles: it counts only the single largest bottle-to-sink
    capacity, never the sum -- so two commensurable bottles that jointly satisfy a demand are wrongly BLOCKED."""
    sink_caps = [c for _u, v, c in edges if v == sink]
    return max(sink_caps) if sink_caps else 0.0


def _fit_inventory_with(**swaps):
    """The full isopentyl fit-bench inventory with named bottles REPLACED by a caller-supplied StockMaterial
    (keyword = one of glacial_acetic/isoamyl/sulfuric/nahco3/nacl/mgso4/water). Every other bottle is the real
    library bottle, generously stocked -- so a swapped-in wrong bottle is the ONLY thing that can move a verdict."""
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


def _named_bottle(material_id, display, name, lo, hi, phase, unit_qty=None):
    """A NAME-keyed single-component StockMaterial (the honest carrier for the ionic auxiliaries) at a chosen
    active-fraction band -- the wrong-formulation bottles the F43 `satisfies_band` mutants (M44-M47) BLOCK on."""
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, material_id, display,
        (MaterialComponent.known(name, "active", lo, hi),), phase, "fixture",
        quantity=unit_qty,
    )


def _route_with_extra_use(route: ExperimentRoute, use: ProcedureMaterialUse) -> ExperimentRoute:
    """A `dataclasses.replace`d LOCAL copy of `route` with one extra `ProcedureMaterialUse` appended to the
    FIRST procedure-bearing operation (the exact "mutate the input" technique, no source edit) -- used to craft
    a two-DISTINCT-SPEC same-species route the corpus does not itself carry (M52)."""
    steps = list(route.steps)
    for i, step in enumerate(steps):
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        ops = list(procedure.operations)
        ops[0] = dc.replace(ops[0], material_uses=ops[0].material_uses + (use,))
        new_procedure = dc.replace(procedure, operations=tuple(ops))
        steps[i] = dc.replace(step, envelope=dc.replace(step.envelope, procedure=new_procedure))
        return dc.replace(route, steps=tuple(steps))
    raise AssertionError("expected a procedure-bearing operation to append a material use to")


def _deformulated_acetic_route() -> ExperimentRoute:
    """The real isopentyl route with the acetic-acid REACTANT use's typed `formulation` field cleared to None
    (a `dataclasses.replace`d LOCAL copy) -- so the generic compiler derives NO composition band for it. F45
    moved the band off a prose scan onto this typed field, so THIS is where a de-formulation now lives. The
    prose still names 'glacial' (untouched), which is exactly what the M56 runtime-prose-scan mutant re-reads."""
    route = _isopentyl_route()
    steps = list(route.steps)
    changed = False
    for i, step in enumerate(steps):
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        new_ops = []
        for op in procedure.operations:
            new_uses = tuple(
                dc.replace(u, formulation=None) if (u.name.strip().casefold() == "acetic acid"
                                                    and u.formulation is not None) else u
                for u in op.material_uses
            )
            if new_uses != op.material_uses:
                changed = True
            new_ops.append(dc.replace(op, material_uses=new_uses))
        steps[i] = dc.replace(step, envelope=dc.replace(step.envelope, procedure=dc.replace(procedure, operations=tuple(new_ops))))
    if not changed:
        raise AssertionError("expected a 'glacial'-formulated acetic-acid material use to de-formulate")
    return dc.replace(route, steps=tuple(steps))


_ACETIC_DIGEST = requirements_mod._struct_digest(resolve_target("acetic acid", InputKind.NAME).canonical())


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
    """Re-targeted for the Round-IV core (`_material_item_status_one`/`_match_interval` DELETED; the material
    verdict is now `assess._comp_phase_status` per bottle). The LAW M4 still guards: an UNGATED requirement
    (no assay/band/phase) that is ABSENT from every declared bottle is an honest possession-UNKNOWN -- never a
    silent FIT. (Present-possession IS legitimately FIT now -- water rides the real FIT-bench material axis on
    exactly that -- so the live hazard is treating IGNORANCE/ABSENCE as satisfaction, the exact "unspecified =
    100%" fabrication, one axis over.) Real: an ungated ethanol requirement, absent from a pure-acetic bottle,
    is UNKNOWN. Mutant: `_comp_phase_status` fabricates a possession FIT for an absent, ungated species."""
    ethanol = _molecule("ethanol")
    stock = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "stock-acetic-pure", "Acetic acid, ACS reagent grade",
        (MaterialComponent.of_molecule(_molecule("acetic acid"), "active", 1.0, 1.0),), Phase.LIQUID, "fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, required_assay=None, phase=None, quantity=None,
        role="reactant", evidence_source="fixture: no sourced purity spec", name="ethanol",
    )
    profile = _profile(material_inventory=(stock,))
    real_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.UNKNOWN

    real_cps = assess_mod._comp_phase_status

    def mutant_comp_phase_status(req, stk):
        result = real_cps(req, stk)
        if (result is None and req.composition_band is None and req.required_assay is None
                and req.phase is None):
            # BUG: an absent, ungated species is assumed present/100%-satisfied (unspecified purity = 100%)
            return CapabilityStatus.FIT, f"{stk.material_id}: BUG unspecified/absent material assumed satisfied"
        return result

    with _patch(assess_mod, "_comp_phase_status", mutant_comp_phase_status):
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
    """Re-expressed SYNTHETICALLY for Round IV: the old "isopentyl bench = overall CAPABILITY_FIT" contract is
    DEAD (no corpus route reaches FIT now). The underlying LAW is untouched -- the tier HARD-LAW: even with
    EVERY axis clean, overall CAPABILITY_FIT requires readiness >= PROCESS_SPECIFIED; a demotion below it caps
    the ceiling to UNKNOWN. Built on a synthetic all-axes-clear `RouteCapabilityRequirements` + empty profile
    (no BLOCKED/UNKNOWN axis anywhere), so the ONLY thing between clean axes and FIT is the tier gate. Real:
    PROCESS_SPECIFIED -> FIT, REACTION_VOUCHED -> UNKNOWN. Mutant: `tier_rank` forced constant (the M10/M11
    tier-gate defeat) lets the demoted, axes-clean case ride to FIT -- FIT survives the readiness demotion."""
    profile = _profile()
    reqs = _reqs()  # every axis NOT_APPLICABLE / UNCONSTRAINED -> nothing BLOCKED, nothing UNKNOWN
    real_full = assess(profile, reqs, _readiness_at(PROCESS_SPECIFIED))
    demoted_readiness = _readiness_at(REACTION_VOUCHED)
    real_demoted = assess(profile, reqs, demoted_readiness)
    real_ok = real_full.overall is CapabilityStatus.FIT and real_demoted.overall is CapabilityStatus.UNKNOWN

    with _patch(assess_mod, "tier_rank", lambda t: 7):  # BUG: every tier compares equal -> the HARD-LAW floor never bites
        mutant_a = assess(profile, reqs, demoted_readiness)
    mutant_bad = mutant_a.overall is CapabilityStatus.FIT
    return real_ok and mutant_bad


# =================================================================================================================
# M23-M38 (Round III)
# =================================================================================================================

@mutant("M23 reaction-class-label-manufactures-universal-assay-floor [RETIRED]")
def m23() -> bool:
    """RETIRED (Round IV, F45). The mechanism M23 tested -- the leaf-whitelist assay floor keyed on
    `requirements._known_leaf_ids()` -- no longer EXISTS: F45 deleted `_KNOWN_LEAF_IDS`, the leaf-whitelist and
    the runtime prose scan, folding reactant material semantics into the SOURCE `ProcedureMaterialUse`s read by
    the generic `_material_requirements`. There is no function left to mutate here. M23's spirit -- the generic
    compiler must not know special target/reagent identities and must not manufacture a requirement from prose
    -- is now carried, on the real object path, by M55 (identity-scoped floor) and M56 (runtime prose scan).
    Reported as a VACUOUS/RETIRED defer, never a fabricated kill."""
    raise Vacuous("RETIRED: leaf-whitelist floor deleted by F45; spirit re-homed on M55 (identity) + M56 (prose)")


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

    def mutant_material_requirements(rt_):
        # BUG (re-targeted for Round IV -- `_procedure_only_material_requirements` was unified INTO
        # `_material_requirements` by F45): the procedure-material projection vanishes, so only bare leaf
        # inputs are demanded and every procedure-only auxiliary (the MgSO4 drier, the washes, the catalyst)
        # is silently dropped from the material axis -- the exact "procedure materials disappear" fault.
        return tuple(
            MaterialRequirement(
                identity=leaf, required_assay=None, phase=None, quantity=None,
                role="reactant (leaf input)", evidence_source="mutant: procedure auxiliaries dropped",
            )
            for leaf in rt_.leaf_inputs
        )

    with _patch(requirements_mod, "_material_requirements", mutant_material_requirements):
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

    # Re-targeted for Round IV: the quantity gate is no longer a per-bottle `_material_item_status_one` check;
    # it is the finite-pool ALLOCATION (`assess._max_flow`, F42). The mutant reverts that finite pool to the
    # pre-F42 "stock is unlimited" behaviour -- a bottle can be spent without ever debiting its capacity -- so
    # the 10 mL-vs-20 mL glacial-acetic shortfall (a provable BLOCK) launders to FIT.
    with _patch(assess_mod, "_max_flow", _unlimited_pool_flow):
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

    # Re-targeted for Round IV: the phase gate now lives in `assess._comp_phase_status`. Scoped to the isoamyl-
    # alcohol requirement ONLY (the neat-LIQUID SUBSTRATE, uniquely: phase declared + no composition band), so
    # stripping it does not trade the alcohol's provable phase BLOCK for some other axis's verdict -- the same
    # M25/M26 "don't move a different requirement" discipline as before.
    isoamyl_digest = requirements_mod._struct_digest(
        resolve_target("isoamyl alcohol", InputKind.NAME).canonical()
    )
    real_cps = assess_mod._comp_phase_status

    def mutant_comp_phase_status(requirement, stock):
        if (
            requirement.phase is not None and requirement.identity is not None
            and requirements_mod._struct_digest(requirement.identity) == isoamyl_digest
        ):
            requirement = dc.replace(requirement, phase=None)  # BUG: phase gate silently dropped
        return real_cps(requirement, stock)

    with _patch(assess_mod, "_comp_phase_status", mutant_comp_phase_status):
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


@mutant("M38 canonical-assessment-loads-after-evidence-altered")
def m38() -> bool:
    """Re-expressed for Round IV: the old "real bench = CAPABILITY_FIT" premise is DEAD, so this no longer
    asserts a FIT dossier (none exists). The LAW it guards is untouched and does NOT need FIT: a canonical
    wire whose carried profile snapshot is TAMPERED (declared stock stripped) must be REFUSED on load, because
    the carried per-route assessment no longer RE-DERIVES under the altered profile. On the real searched
    isopentyl bench (overall UNKNOWN, but material axis FIT off the declared stock), stripping the inventory
    flips the re-derived material axis FIT->UNKNOWN -- a detectable divergence. The pin
    (`capability_question_digest`) is forged CONSISTENTLY with the tampered profile first (a stale pin would
    catch the tamper on its own -- a shallower guard than CAPABILITY-REBIND-ON-LOAD), isolating the
    re-derivation guard. Mutant: that guard is disabled, and the forged wire loads with the stale assessment."""
    resp = _fit_response()
    # a real per-route assessment whose material axis rests on the declared stock (the thing we will strip).
    assert any(
        d.capability_assessment and d.capability_assessment.material.status is CapabilityStatus.FIT
        for d in resp.ranked_route_dossiers
    )
    payload = response_to_payload(resp)  # include_replay=True default -> CANONICAL_VERIFIED
    cp = payload["request"]["capability_profile"]
    for f in cp["fields"]:
        if f[0] == "material_inventory":
            f[1]["items"] = []  # strip the declared stock the material-axis FIT depended on
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
            response_from_payload(payload)
            mutant_loads = True  # the stale, no-longer-re-deriving assessment loaded unchallenged
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


# =================================================================================================================
# M41-M62 (Round IV -- the F41-F62 composition/conservation/genericity/derived-data findings)
# =================================================================================================================

@mutant("M41 repeated-use-keeps-first-not-whole-route-sum")
def m41() -> bool:
    """F41: a species used across several operations demands the SUM of its commensurable draws (water:
    55 + 10 + 25 = 90 mL), never a first-value-wins truncation. Real: a fit bench stocking only 80 mL water
    BLOCKS on the 90 mL whole-route demand. Mutant: `_sum_commensurable` keeps the FIRST draw (55 mL), which
    the 80 mL bottle covers -> a fabricated FIT that undercounts the real demand."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    bench = isopentyl_capability_fit_bench(
        material_inventory=_fit_inventory_with(water=material_library.wash_water(quantity=StockQuantity.of("80", "mL"))),
    )
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    def mutant_sum(quantities):
        present = [q for q in quantities if q is not None]
        return present[0] if present else None  # BUG: first draw wins, the rest of the route's demand vanishes

    with _patch(requirements_mod, "_sum_commensurable", mutant_sum):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M42 one-finite-bottle-satisfies-two-independent-demands")
def m42() -> bool:
    """F42: material inventory is a FINITE resource -- one 30 mL bottle cannot satisfy two independent 20 mL
    demands (40 mL total > 30 mL capacity). Real: the finite-pool max-flow allocation BLOCKS. Mutant: `_max_flow`
    reverts to the pre-F42 "stock is unlimited" ledger, so the single bottle is spent twice -> FIT."""
    ethanol = _molecule("ethanol")
    bottle = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "one-30ml-ethanol", "Ethanol, one 30 mL bottle",
        (MaterialComponent.of_molecule(ethanol, "active", 1.0, 1.0),), Phase.LIQUID, "fixture",
        quantity=StockQuantity.of("30", "mL"),
    )
    demand = MaterialRequirement(
        identity=ethanol, required_assay=None, phase=None, quantity=StockQuantity.of("20", "mL"),
        role="reactant", evidence_source="fixture", name="ethanol",
    )
    reqs = _reqs(material=(demand, dc.replace(demand, role="reactant (second independent draw)")))
    profile = _profile(material_inventory=(bottle,))
    real_a = assess(profile, reqs, _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    with _patch(assess_mod, "_max_flow", _unlimited_pool_flow):
        mutant_a = assess(profile, reqs, _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M43 compatible-bottles-fail-to-combine-toward-one-demand")
def m43() -> bool:
    """F42 (allocation, the other direction): several COMMENSURABLE bottles MAY jointly satisfy one demand --
    two 25 mL bottles cover a 40 mL draw. Real: the max-flow allocation combines them -> FIT. Mutant: `_max_flow`
    counts only the single largest bottle (25 mL) and never combines them -> a false BLOCK on a demand the bench
    can actually meet."""
    ethanol = _molecule("ethanol")
    two_bottles = tuple(
        StockMaterial(
            STOCK_MATERIAL_SCHEMA, f"ethanol-25ml-{i}", f"Ethanol, 25 mL bottle #{i}",
            (MaterialComponent.of_molecule(ethanol, "active", 1.0, 1.0),), Phase.LIQUID, "fixture",
            quantity=StockQuantity.of("25", "mL"),
        )
        for i in (1, 2)
    )
    demand = MaterialRequirement(
        identity=ethanol, required_assay=None, phase=None, quantity=StockQuantity.of("40", "mL"),
        role="reactant", evidence_source="fixture", name="ethanol",
    )
    reqs = _reqs(material=(demand,))
    profile = _profile(material_inventory=two_bottles)
    real_a = assess(profile, reqs, _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.FIT

    with _patch(assess_mod, "_max_flow", _single_bottle_flow):
        mutant_a = assess(profile, reqs, _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.BLOCKED
    return real_ok and mutant_bad


@mutant("M44 formulation-erased-before-assessment")
def m44() -> bool:
    """F43: a sourced FORMULATION ('5% aqueous') becomes a typed composition BAND the wash requirement carries
    -- so an over-concentrated bottle BLOCKS on the band's ceiling. Real: a 50-60% "NaHCO3 wash" bottle BLOCKS
    the 5%-band requirement. Mutant: `_formulation_spec` erases the formulation (band -> None), leaving a bare
    possession requirement that the over-concentrated bottle silently clears -> FIT."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    overconc = _named_bottle("nahco3-overconc", "Sodium bicarbonate, over-concentrated",
                             "sodium bicarbonate", 0.5, 0.6, Phase.AQUEOUS_SOLUTION,
                             unit_qty=StockQuantity.of("500", "mL"))
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(nahco3=overconc))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    with _patch(requirements_mod, "_formulation_spec", lambda formulation: (None, None, None)):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M45 hydrated-drier-satisfies-anhydrous")
def m45() -> bool:
    """F43: a HYDRATED magnesium-sulfate bottle (bound water -> low anhydrous fraction, [0.5, 0.6]) cannot
    satisfy the drier's ANHYDROUS band [0.97, 1.0]. Real: `satisfies_band` returns INSUFFICIENT -> BLOCKED.
    Mutant: `satisfies_band` stops consulting the band at all (identity present => SATISFIES) -> the hydrate
    clears the anhydrous requirement -> FIT."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    hydrate = _named_bottle("mgso4-heptahydrate", "Magnesium sulfate heptahydrate (hydrated)",
                            "magnesium sulfate", 0.5, 0.6, Phase.SOLID, unit_qty=StockQuantity.of("250", "g"))
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(mgso4=hydrate))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    real_band = stock_mod.StockMaterial.satisfies_band

    def mutant_satisfies_band(self, key, *, low, high):
        if self.active_fraction_interval(key) is not None:  # BUG: band never consulted -- presence is enough
            return stock_mod.FitnessVerdict.SATISFIES
        return real_band(self, key, low=low, high=high)

    with _patch(stock_mod.StockMaterial, "satisfies_band", mutant_satisfies_band):
        mutant_a = assess(bench, compile_capability_requirements(route), readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M46 over-concentrated-satisfies-5pct-wash")
def m46() -> bool:
    """F43 (`satisfies_band` CEILING): a ~100% bicarbonate bottle is NOT a '5% NaHCO3 wash' -- the band
    [0.045, 0.055] carries a real ceiling. Real: INSUFFICIENT -> BLOCKED. Mutant: the floor-only bug (check
    only `s_lo >= low`, drop the ceiling) waves the over-concentrated stock through -> FIT."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    overconc = _named_bottle("nahco3-neat", "Sodium bicarbonate, ~100% (mislabelled 5% wash)",
                             "sodium bicarbonate", 0.99, 1.0, Phase.AQUEOUS_SOLUTION,
                             unit_qty=StockQuantity.of("500", "mL"))
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(nahco3=overconc))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    def mutant_satisfies_band(self, key, *, low, high):
        interval = self.active_fraction_interval(key)
        if interval is None:
            return stock_mod.FitnessVerdict.IDENTITY_ABSENT
        s_lo, _s_hi = interval
        if s_lo >= float(low):  # BUG: floor-only -- the band's CEILING is never checked
            return stock_mod.FitnessVerdict.SATISFIES
        return stock_mod.FitnessVerdict.INSUFFICIENT_ASSAY

    with _patch(stock_mod.StockMaterial, "satisfies_band", mutant_satisfies_band):
        mutant_a = assess(bench, compile_capability_requirements(route), readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M47 unsaturated-satisfies-saturated-brine")
def m47() -> bool:
    """F43 (`satisfies_band` FLOOR): a dilute (2-3%) NaCl solution is NOT a SATURATED brine -- the band
    [0.20, 1.0] carries a real floor. Real: INSUFFICIENT -> BLOCKED. Mutant: the ceiling-only bug (check only
    `s_hi <= high`, drop the floor) lets the unsaturated stock clear the saturated-brine requirement -> FIT."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    dilute = _named_bottle("nacl-dilute", "Sodium chloride, dilute (unsaturated)",
                           "sodium chloride", 0.02, 0.03, Phase.AQUEOUS_SOLUTION,
                           unit_qty=StockQuantity.of("250", "mL"))
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(nacl=dilute))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    def mutant_satisfies_band(self, key, *, low, high):
        interval = self.active_fraction_interval(key)
        if interval is None:
            return stock_mod.FitnessVerdict.IDENTITY_ABSENT
        _s_lo, s_hi = interval
        if s_hi <= float(high):  # BUG: ceiling-only -- the band's FLOOR is never checked
            return stock_mod.FitnessVerdict.SATISFIES
        return stock_mod.FitnessVerdict.INSUFFICIENT_ASSAY

    with _patch(stock_mod.StockMaterial, "satisfies_band", mutant_satisfies_band):
        mutant_a = assess(bench, compile_capability_requirements(route), readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M48 structure-known-requirement-FITs-name-only-stock")
def m48() -> bool:
    """F44: a requirement with a KNOWN structure identity may only be satisfied by structure-keyed evidence --
    a bare NAME bottle is weaker and can never stand in for a proven structure. Real: a structure-known ethanol
    requirement, against a stock that carries ethanol only under a NAME key, is absent under the allowed key ->
    BLOCKED. Mutant: `_species_key_in` falls back to the name after the structure is absent -> the name-only
    bottle wrongly satisfies -> FIT."""
    ethanol = _molecule("ethanol")
    name_only = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "ethanol-name-only", "Ethanol (declared by name only)",
        (MaterialComponent.known("ethanol", "active", 0.95, 0.99),), Phase.LIQUID, "fixture",
    )
    requirement = MaterialRequirement(
        identity=ethanol, required_assay=0.9, phase=None, quantity=None,
        role="reactant", evidence_source="fixture: structure-known", name="ethanol",
    )
    profile = _profile(material_inventory=(name_only,))
    real_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    def mutant_species_key_in(req, stock):
        if req.identity is not None and stock.active_fraction_interval(req.identity) is not None:
            return req.identity
        # BUG (F44 downgrade): after the structure is absent, fall back to the weaker NAME key
        if req.name is not None and stock.active_fraction_interval(req.name) is not None:
            return req.name
        return None

    with _patch(assess_mod, "_species_key_in", mutant_species_key_in):
        mutant_a = assess(profile, _reqs(material=(requirement,)), _ps_readiness())
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M49 hazard-unresolved-displayed-but-containment-FIT")
def m49() -> bool:
    """F47: a required procedure material whose hazard status is UNRESOLVED means the containment capability it
    needs cannot be determined -> the containment axis caps at UNKNOWN, never a pass. Real: the isopentyl route
    carries unresolved ionic-auxiliary hazards, so containment reads UNKNOWN under the fully-equipped fit bench
    (which owns the FUME_HOOD). Mutant: `_procedure_hazard_scan` still forces the hood but DROPS the unresolved
    leg, so the F47 cap never fires and the axis stays FIT -- the hazard merely displayed, not gating."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    bench = isopentyl_capability_fit_bench()
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.containment.status is CapabilityStatus.UNKNOWN

    real_scan = requirements_mod._procedure_hazard_scan

    def mutant_scan(rt_):
        forces, reasons, _unresolved = real_scan(rt_)
        return forces, reasons, ()  # BUG: unresolved hazards dropped -> F47 cap never triggers

    with _patch(requirements_mod, "_procedure_hazard_scan", mutant_scan):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.containment.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M50 unassessed-byproduct-becomes-AQUEOUS_NEUTRAL [VERIFIED-DEFER]")
def m50() -> bool:
    """VERIFIED-DEFER (F48). The F48 branch is present + guarded (`requirements._waste_requirement`: a byproduct
    with `hazard_name is None` is pushed to `WasteRequirement.unresolved`, never AQUEOUS_NEUTRAL-by-negation --
    confirmed by reading). But the forcing corpus emits only an ASSESSED-benign water byproduct, so the branch
    is corpus-unreachable, AND it cannot be exercised on a real object path within harness scope: a byproduct
    with `hazard_name=None` must come from a route whose `verify_handling` produces one, which needs a fabricated
    ExperimentRoute + RouteHandling (a synthetic route, not a real searched object) -- and even injecting one via
    the real route leaves that route's own 5 spent-stream UNRESOLVED entries pinning the waste axis at UNKNOWN
    under BOTH honest and mutant, so the discriminator cannot flip. The F48 UNKNOWN-cap it feeds IS killed on the
    real path by M51 (spent streams, same waste-axis cap). A true M50 kill needs a synthetic-route corpus (0.9.5).
    A defer is a finding, never a fabricated kill."""
    raise Vacuous("F48 branch present+guarded; corpus emits no unassessed byproduct; not constructible on a real "
                  "object path in scope (would need a synthetic route+handling); its UNKNOWN-cap killed by M51")


@mutant("M51 spent-workup-streams-omitted-waste-FIT")
def m51() -> bool:
    """F48/F49: every spent workup stream (wash/rinse/drier/brine) the source leaves without a disposal routing
    is an UNRESOLVED waste stream that caps the waste axis at UNKNOWN. Real: the isopentyl route's 5 spent
    streams make waste UNKNOWN under the fit bench (which routes AQUEOUS_NEUTRAL). Mutant: `_waste_requirement`
    drops the unresolved streams, so the waste axis clears to FIT -- the spent-stream obligation silently
    vanishes."""
    route = _isopentyl_route()
    readiness = evaluate_route(route)
    bench = isopentyl_capability_fit_bench()
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.waste.status is CapabilityStatus.UNKNOWN

    real_waste = requirements_mod._waste_requirement

    def mutant_waste(rt_):
        w = real_waste(rt_)
        return WasteRequirement(w.categories, w.reasons, ())  # BUG: spent streams omitted

    with _patch(requirements_mod, "_waste_requirement", mutant_waste):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.waste.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M52 two-distinct-specs-of-one-species-deduped-by-identity")
def m52() -> bool:
    """F50: two uses of one species at DIFFERENT semantic specs (formulation/band/phase) are DISTINCT demands
    that must never collapse to one. A crafted route charges acetic acid twice -- once glacial (band [0.99, 1.0])
    and once as a hypothetical '5% aqueous' wash (band [0.045, 0.055]). Real: `_material_requirements` keeps them
    SEPARATE (spec-in-key), so the 5%-aqueous demand BLOCKS against the glacial-acetic bottle -> BLOCKED. Mutant:
    grouping by species identity ALONE dedupes them to the first (glacial) spec, which the bottle satisfies -> FIT."""
    acetic = _molecule("acetic acid")
    extra = ProcedureMaterialUse(
        name="acetic acid", role=ProcedureMaterialRole.WASH, identity=acetic,
        formulation="5% aqueous", phase=Phase.AQUEOUS_SOLUTION,
        evidence_source="fixture: a SECOND, distinct-spec acetic-acid use (F50 probe)",
    )
    route = _route_with_extra_use(_isopentyl_route(), extra)
    readiness = evaluate_route(route)
    bench = isopentyl_capability_fit_bench()
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.BLOCKED

    real_material_requirements = requirements_mod._material_requirements

    def mutant_material_requirements(rt_):
        # BUG (F50): dedupe by species IDENTITY alone -- the spec drops out of the key, so the two distinct-spec
        # acetic-acid uses collapse to ONE requirement carrying the first (glacial) spec.
        by_species: "dict[str, MaterialRequirement]" = {}
        order: "list[str]" = []
        for r in real_material_requirements(rt_):
            key = requirements_mod._struct_digest(r.identity) if r.identity is not None \
                else f"name:{(r.name or '').strip().casefold()}"
            if key not in by_species:
                by_species[key] = r
                order.append(key)
        return tuple(by_species[k] for k in order)

    with _patch(requirements_mod, "_material_requirements", mutant_material_requirements):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M53 DAG-capability-request-accepted-but-unassessed")
def m53() -> bool:
    """F51: a capability profile requested together with the CAPPED_SCISSION_CONVERGENT (convergent-DAG) grammar
    must be a typed REFUSED -- the DAG admission model carries NO capability-topology, so a verdict cannot be
    honestly computed. This is a NEGATIVE property with no severable helper to sever (the guard is an inline
    conditional at the top of `_run_recompile`), so -- exactly as M7/M8/M34/M36 do for the profile-noninterference
    laws -- it is proved by the COUNTERFACTUAL the guard prevents: the SAME convergent search run WITHOUT a
    profile really does proceed to a non-refused response whose dossiers carry NO capability_assessment (the
    profile is dropped on the floor in DAG mode, F51). Real: (profile + convergent) is REFUSED, diagnostic names
    the capability drop. Counterfactual (the silent-unassessed pass the guard blocks): (no profile + convergent)
    is NOT refused and answers the capability question with nothing."""
    profiled = build_recompile_request(
        "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
        grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    resp_profiled = run_compilation(profiled)
    real_ok = (
        resp_profiled.outcome.value == "REFUSED"
        and any("capab" in d.lower() and "convergent" in d.lower() for d in resp_profiled.diagnostics)
    )

    unprofiled = build_recompile_request(
        "isopentyl acetate", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    resp_unprofiled = run_compilation(unprofiled)
    # the guard-removed world: a convergent search silently proceeds with no capability answer anywhere.
    no_capability_anywhere = all(
        getattr(d, "capability_assessment", None) is None for d in resp_unprofiled.ranked_route_dossiers
    )
    mutant_bad = resp_unprofiled.outcome.value != "REFUSED" and no_capability_anywhere
    return real_ok and mutant_bad


@mutant("M54 compile-human-drops-capability-while-JSON-honors-it")
def m54() -> bool:
    """F52: the `compile`/`recompile` HUMAN render and the `--json` payload must answer the capability question
    identically (human == JSON). Real: the human render carries a `CAPABILITY[...]` block and the JSON payload
    carries a `capability_assessment` for the same route. Mutant: the shared `render_capability_lines` returns
    nothing (the human path drops the capability block) while the JSON codec -- a SEPARATE path -- still emits
    the assessment, so the two surfaces disagree and a human reader loses the capability answer entirely."""
    from smartchem.cli import _render_recompile_response
    resp = _fit_response()
    human = _render_recompile_response(resp, quiet=False)
    payload = response_to_payload(resp)
    json_has = any(d.get("capability_assessment") for d in payload["ranked_route_dossiers"])
    real_ok = "CAPABILITY[" in human and json_has

    def mutant_render_capability_lines(assessment, origin, *, indent):
        return []  # BUG: the human capability block is dropped; the JSON codec path is untouched

    with _patch(svc, "render_capability_lines", mutant_render_capability_lines):
        human2 = _render_recompile_response(resp, quiet=False)
    mutant_bad = "CAPABILITY[" not in human2 and json_has
    return real_ok and mutant_bad


@mutant("M55 generic-compiler-knows-a-special-reagent-identity")
def m55() -> bool:
    """F45: the generic requirements compiler must carry NO target/reagent-specific identities. A de-formulated
    acetic-acid use (its typed 'glacial' formulation cleared) earns NO composition floor -- so a modest 90%
    acetic bottle satisfies it. Real: FIT. Mutant: `_material_requirements` re-introduces an IDENTITY-scoped
    esterification floor (assay >= 0.98 for anything whose structure IS acetic acid), which the 90% bottle now
    BLOCKS -- special-identity knowledge smuggled back into the generic layer."""
    route = _deformulated_acetic_route()
    readiness = evaluate_route(route)
    modest_acetic = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-90pct", "Acetic acid, 90% technical grade",
        (MaterialComponent.of_molecule(_molecule("acetic acid"), "active", 0.90, 0.92),), Phase.LIQUID, "fixture",
        quantity=StockQuantity.of("500", "mL"),
    )
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(glacial_acetic=modest_acetic))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.FIT

    real_material_requirements = requirements_mod._material_requirements

    def mutant_material_requirements(rt_):
        out = []
        for r in real_material_requirements(rt_):
            if r.identity is not None and requirements_mod._struct_digest(r.identity) == _ACETIC_DIGEST:
                # BUG (F45): a floor manufactured from the reagent's IDENTITY, not from sourced evidence
                r = dc.replace(r, required_assay=0.98, composition_band=None,
                               evidence_source="mutant: identity-scoped esterification floor (F45 violation)")
            out.append(r)
        return tuple(out)

    with _patch(requirements_mod, "_material_requirements", mutant_material_requirements):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.BLOCKED
    return real_ok and mutant_bad


@mutant("M56 runtime-glacial-prose-scan-manufactures-a-requirement")
def m56() -> bool:
    """F45: the generic compiler must not RUNTIME-SCAN procedure prose to manufacture a requirement. The
    de-formulated acetic use no longer carries a typed 'glacial' formulation, but the procedure PROSE still says
    'glacial'. Real: the compiler reads the typed field only -> no floor -> a modest 90% acetic bottle FITs.
    Mutant: `_material_requirements` re-scans the prose for 'glacial' and manufactures a >= 0.99 floor on the
    acetic requirement -- the exact retired runtime prose scan -- which the 90% bottle now BLOCKS."""
    route = _deformulated_acetic_route()
    readiness = evaluate_route(route)
    modest_acetic = StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-90pct-b", "Acetic acid, 90% technical grade",
        (MaterialComponent.of_molecule(_molecule("acetic acid"), "active", 0.90, 0.92),), Phase.LIQUID, "fixture",
        quantity=StockQuantity.of("500", "mL"),
    )
    bench = isopentyl_capability_fit_bench(material_inventory=_fit_inventory_with(glacial_acetic=modest_acetic))
    real_a = assess(bench, compile_capability_requirements(route), readiness)
    real_ok = real_a.material.status is CapabilityStatus.FIT

    def _procedure_prose(rt_):
        chunks = []
        for step in rt_.steps:
            procedure = step.envelope.procedure
            if procedure is None:
                continue
            if procedure.scale is not None and isinstance(procedure.scale.value, str):
                chunks.append(procedure.scale.value)
            for op in procedure.operations:
                if op.quantity is not None and isinstance(op.quantity.value, str):
                    chunks.append(op.quantity.value)
                chunks.extend(op.materials)
        return " ".join(chunks).casefold()

    real_material_requirements = requirements_mod._material_requirements

    def mutant_material_requirements(rt_):
        has_glacial = "glacial" in _procedure_prose(rt_)
        out = []
        for r in real_material_requirements(rt_):
            if has_glacial and r.name is not None and "acetic acid" in r.name.casefold():
                # BUG (F45): a floor manufactured from a RUNTIME free-text scan of the procedure prose
                r = dc.replace(r, required_assay=0.99, composition_band=None,
                               evidence_source="mutant: runtime 'glacial' prose scan (F45 violation)")
            out.append(r)
        return tuple(out)

    with _patch(requirements_mod, "_material_requirements", mutant_material_requirements):
        req2 = compile_capability_requirements(route)
        mutant_a = assess(bench, req2, readiness)
    mutant_bad = mutant_a.material.status is CapabilityStatus.BLOCKED
    return real_ok and mutant_bad


@mutant("M57 solubility-treated-as-solution-mass-fraction")
def m57() -> bool:
    """F46: a DerivedIntervalEvidence record refuses to exist unless `derivation_fn(*inputs) == value_interval`.
    Real: the CORRECT NaCl brine record (value interval = solution_fraction_from_solubility(35.7, 36) via
    x = s/(s+100)) constructs and verifies. Mutant: the g/100 g-water solubility figure dropped STRAIGHT into a
    mass-fraction slot (0.357, 0.36) while the derivation reconstructs 0.263.. -> the construction check raises,
    refusing the mislabelled interval at build time."""
    s_lo, s_hi = Fraction(357, 10), Fraction(36)
    honest = DerivedIntervalEvidence(
        derivation_id="m57-nacl-correct",
        value_interval=solution_fraction_from_solubility(s_lo, s_hi),
        unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
        source_locator="fixture: NaCl solubility 35.7-36 g/100 g water",
        derivation_method=DerivationMethod.UNIT_CONVERTED,
        derivation_inputs=(s_lo, s_hi),
        derivation_fn=solution_fraction_from_solubility,
        domain_of_validity="aqueous NaCl at saturation, 20-25 C",
    )
    real_ok = honest.verify()

    raised = False
    try:
        DerivedIntervalEvidence(
            derivation_id="m57-nacl-unit-bug",
            value_interval=(s_lo / 100, s_hi / 100),  # BUG: g/100 g-water used AS a mass fraction of solution
            unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
            source_locator="fixture: NaCl solubility 35.7-36 g/100 g water",
            derivation_method=DerivationMethod.UNIT_CONVERTED,
            derivation_inputs=(s_lo, s_hi),
            derivation_fn=solution_fraction_from_solubility,
            domain_of_validity="aqueous NaCl at saturation, 20-25 C",
        )
    except ValueError:
        raised = True
    return real_ok and raised


@mutant("M58 decorative-uncertainty-as-DERIVED [+residual-flagged]")
def m58() -> bool:
    """F46: the DerivedIntervalEvidence construction check KILLS an arithmetic/width error -- a claimed band that
    its own inputs do not reconstruct is refused. Real: an ASSUMED symmetric band [0.045, 0.055] whose inputs
    (0.05 +- 0.005) reconstruct it constructs. Mutant: a claimed +-1% band [0.04, 0.06] whose inputs still say
    +-0.5% -> reconstruction mismatch -> refused.

    RESIDUAL (verified + flagged for 0.9.5, per the adversary's unease): the guard enforces ARITHMETIC
    reconstruction, NOT method-label provenance. A DECORATIVE width that IS arithmetically consistent but is
    mislabelled a measured/derived method (BROADENED) instead of ASSUMED constructs FINE -- the guard cannot
    catch it. This mutant therefore honestly kills a unit/arithmetic error, NOT a mislabelled-but-consistent
    width. The residual is printed below and does NOT count toward the kill."""
    nominal, half = Fraction(5, 100), Fraction(5, 1000)
    honest = DerivedIntervalEvidence(
        derivation_id="m58-assumed-consistent",
        value_interval=symmetric_band(nominal, half),
        unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
        source_locator="fixture: nominal 5% wash, +-0.5% ASSUMED bench tolerance",
        derivation_method=DerivationMethod.ASSUMED,
        derivation_inputs=(nominal, half),
        derivation_fn=symmetric_band,
        domain_of_validity="bench-prepared 5% w/w aqueous NaHCO3 wash (band assumed)",
    )
    real_ok = honest.verify()

    raised = False
    try:
        DerivedIntervalEvidence(
            derivation_id="m58-width-bug",
            value_interval=(Fraction(4, 100), Fraction(6, 100)),  # BUG: claims +-1% but inputs say +-0.5%
            unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
            source_locator="fixture: nominal 5% wash",
            derivation_method=DerivationMethod.ASSUMED,
            derivation_inputs=(nominal, half),
            derivation_fn=symmetric_band,
            domain_of_validity="bench-prepared 5% w/w aqueous NaHCO3 wash",
        )
    except ValueError:
        raised = True

    residual_constructs = False
    try:
        DerivedIntervalEvidence(
            derivation_id="m58-mislabelled-but-consistent",
            value_interval=symmetric_band(nominal, half),
            unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
            source_locator="fixture: decorative width mislabelled a measured spread",
            derivation_method=DerivationMethod.BROADENED,  # mislabelled: implies a measured spread, width is decorative
            derivation_inputs=(nominal, half),
            derivation_fn=symmetric_band,
            domain_of_validity="bench-prepared 5% w/w aqueous NaHCO3 wash",
        )
        residual_constructs = True
    except ValueError:
        residual_constructs = False
    print(f"    [M58 RESIDUAL] mislabelled-but-arithmetically-consistent decorative width constructed="
          f"{residual_constructs} -- the guard is ARITHMETIC-only (no method-label provenance check); "
          f"flag for 0.9.5. This does NOT count toward the M58 kill.", flush=True)
    return real_ok and raised


@mutant("M59 legacy-v0.8-response-decoder-fabricates-capability")
def m59() -> bool:
    """F54 (distinct from M37): the LEGACY-PAYLOAD MIGRATION path. A v0.8 ranked-route dossier predates the
    capability field, so its payload has NO `capability_assessment` key; the additive-optional decoder must map
    that absence to `None` (NOT_REQUESTED), never a fabricated assessment. M37 tests the response-level coherence
    GUARD on a FORGED-live object; M59 tests the CODEC seam -- `_capability_assessment_from_payload` invoked by
    `ranked_summary_from_payload` on a key-stripped (v0.8-shaped) dossier. Real: absent key -> None. Mutant: the
    decoder fabricates an assessment for a missing/legacy field."""
    resp = run_compilation(build_recompile_request(_FAST_TARGET, max_depth=2))  # no profile -> NOT_REQUESTED
    dossier_payload = dict(response_to_payload(resp)["ranked_route_dossiers"][0])
    dossier_payload.pop("capability_assessment", None)  # simulate a v0.8 wire predating the field
    real_summary = ranked_summary_from_payload(dossier_payload)
    real_ok = real_summary.capability_assessment is None

    fabricated = assess(_profile(), _reqs(), _ps_readiness())
    real_from_payload = svc._capability_assessment_from_payload

    def mutant_from_payload(payload):
        if payload is None:  # BUG: a missing/legacy capability field fabricates an assessment
            return fabricated
        return real_from_payload(payload)

    with _patch(svc, "_capability_assessment_from_payload", mutant_from_payload):
        mutant_summary = ranked_summary_from_payload(dossier_payload)
    mutant_bad = mutant_summary.capability_assessment is not None
    return real_ok and mutant_bad


@mutant("M60 source-substituted-use-stays-digest-identical")
def m60() -> bool:
    """F43/F50: a material requirement's `evidence_source` is load-bearing provenance and must FLOW INTO its
    canonical digest -- two otherwise-identical requirements that differ only in their sourced evidence carry
    DIFFERENT digests (a source substitution is a real change). Real: the two digests differ. Mutant (the same
    "mutate the ONE governing pin" technique as M7/M8/M20): a digest BLIND to `evidence_source` -- simulated by
    normalising that one field to a constant -- collapses the two source-substituted uses to a single identity,
    proving the field is the only distinguisher and that dropping it from the digest would launder a substitution."""
    r1 = MaterialRequirement(
        identity=None, name="acetic acid", required_assay=None, phase=None, quantity=None,
        role="reactant", evidence_source="LibreTexts isopentyl-acetate experiment, operation 1",
    )
    r2 = dc.replace(r1, evidence_source="a DIFFERENT, substituted source citation")
    real_ok = canonical_digest(r1) != canonical_digest(r2)

    blind1 = dc.replace(r1, evidence_source="CONSTANT")
    blind2 = dc.replace(r2, evidence_source="CONSTANT")
    mutant_bad = canonical_digest(blind1) == canonical_digest(blind2)
    return real_ok and mutant_bad


@mutant("M61 partial-ProcessBounds-launders-an-unmet-time-demand")
def m61() -> bool:
    """F56: a real route TIME demand on a process dimension the bench leaves UNMODELED (its bound is None) cannot
    be certified -> the process axis caps at UNKNOWN, never a silent FIT. Fixture: a route declaring an ACTIVE-time
    demand + `workup_included=True` (so the delegate returns FITS on the modelled elapsed dimension), against a
    bench that bounds STEP time but NOT active time. Real: the per-dimension fail-close (`_PROCESS_FAILCLOSE_DIMENSIONS`)
    catches the unmodelled active-time demand -> UNKNOWN. Mutant: the per-dimension table is emptied (pre-F56), so
    the delegate's FITS rides straight through -> a fabricated process FIT."""
    req = ProcessRequirements(
        workup_included=True, provenance="fixture",
        elapsed_minutes=Interval(0, 60, "min"), active_minutes=Interval(0, 30, "min"),
    )
    bounds = ProcessBounds.of(max_step_minutes=1000.0)  # bounds elapsed, NOT active time
    real_axis = assess_mod._process_axis((req,), bounds)
    real_ok = real_axis.status is CapabilityStatus.UNKNOWN

    with _patch(assess_mod, "_PROCESS_FAILCLOSE_DIMENSIONS", ()):  # BUG: pre-F56, no per-dimension fail-close
        mutant_axis = assess_mod._process_axis((req,), bounds)
    mutant_bad = mutant_axis.status is CapabilityStatus.FIT
    return real_ok and mutant_bad


@mutant("M62 attention-agitation-dropped-from-process-failclose-table")
def m62() -> bool:
    """F62 (Wave-C P0): the F56 per-dimension process fail-close is driven off the module-level table
    `_PROCESS_FAILCLOSE_DIMENSIONS`, whose LAST TWO entries (attention mode, agitation mode) were the two a
    hand-written checklist originally dropped -- letting a bench that bounds time but NOT attention wave a
    CONTINUOUS-attention route to process FIT -> overall CAPABILITY_FIT. Fixture: a CONTINUOUS-attention route
    (delegate FITS on the modelled elapsed dimension) against a bench that bounds step time but declares no
    attention. Real: the table catches the unmodelled attention demand -> UNKNOWN. Mutant: the table is reverted
    to the pre-F62 checklist (last two entries dropped), so attention falls through -> FIT."""
    req = ProcessRequirements(
        attention=Attention.CONTINUOUS, workup_included=True, provenance="fixture",
        elapsed_minutes=Interval(0, 60, "min"),
    )
    bounds = ProcessBounds.of(max_step_minutes=1000.0)  # bounds time, NOT attention/agitation
    real_axis = assess_mod._process_axis((req,), bounds)
    real_ok = real_axis.status is CapabilityStatus.UNKNOWN

    pre_f62_table = assess_mod._PROCESS_FAILCLOSE_DIMENSIONS[:-2]  # drop attention + agitation (the F62 regression)
    assert len(pre_f62_table) == 3, "expected the current table to carry 5 dimensions (3 time + 2 mode)"
    with _patch(assess_mod, "_PROCESS_FAILCLOSE_DIMENSIONS", pre_f62_table):
        mutant_axis = assess_mod._process_axis((req,), bounds)
    mutant_bad = mutant_axis.status is CapabilityStatus.FIT

    # Also drive it end-to-end to overall CAPABILITY_FIT (mirrors M61's synthetic-axes shape): a real isopentyl
    # readiness (PROCESS_SPECIFIED) + an all-other-axes-neutral requirements record carrying ONLY this process
    # demand, under an empty profile whose ProcessBounds bounds step time but not attention.
    reqs = _reqs(process=(req,))
    neutral_profile = _profile(process_bounds=bounds)
    real_overall = assess(neutral_profile, reqs, _ps_readiness()).overall is CapabilityStatus.UNKNOWN
    with _patch(assess_mod, "_PROCESS_FAILCLOSE_DIMENSIONS", pre_f62_table):
        mutant_overall = assess(neutral_profile, reqs, _ps_readiness()).overall is CapabilityStatus.FIT
    return real_ok and mutant_bad and real_overall and mutant_overall


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
    print(f"v0.9 capability compiler mutation gate (M1-M62 RC Round IV, {len(_MUTANTS)} mutants registered):",
          flush=True)
    results = run()
    killed = sum(1 for _, k, _ in results if k is True)
    vacuous = sum(1 for _, k, _ in results if k is None)
    survived = sum(1 for _, k, _ in results if k is False)
    print(f"\n{killed}/{len(results)} mutants killed. {vacuous} VACUOUS (RETIRED/VERIFIED-DEFER). "
          f"{survived} SURVIVED (real gap).")
    return 0 if survived == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
