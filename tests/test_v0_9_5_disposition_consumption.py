"""0.9.5 S10 -- the CONSUMPTION of StreamDisposition: ``derive_waste``'s law L1, the latent defects it would otherwise
make unsound (D-C1 / D-C2 / D-C4), the regression differential, and the synthetic reachability witness (freeze §6).

Chart summary, for whoever reads this after me:

* **L1.** A disposition is looked up by its EXACT subject inside its own step's procedure, discharges exactly ONE
  obligation, and ROUTED only ever ADDS a category (derived categories are unioned, never swapped). It discharges
  nothing on an unaccepted source, on non-SOURCE_QUOTED evidence (a hand-forged record that skipped construction), on
  a value that obligation does not admit, on a RECOVERED without a real recovery op, on a species-level ROUTED with no
  hazard record (L3), or on a ROUTED that contradicts the derived fate -- and each refusal leaves the obligation
  UNKNOWN, never BLOCKED.
* **The differential.** With no dispositions the output is byte-identical to the frozen pre-S10 projection (a verbatim
  copy lives below as the oracle) on every fixture that repeats no species across steps; on a route that does, it is a
  strict SUPERSET (D-C2 -- the safe direction).
* **The witness** is a MODEL-LEVEL object: the synthetic DME route from the zero-fit theorem file plus three
  dispositions. It is not a real procedure, it states no real laboratory's disposal practice, and it exists only to
  prove CAPABILITY_FIT is REPRESENTABLE -- that the evaluator is not overconstrained -- while every production corpus
  route stays below it (no cited corpus page states disposal).
"""
from __future__ import annotations

import dataclasses as dc
from functools import lru_cache

import pytest

from smartchem import decompiler_conditions
from smartchem.capability.assess import assess
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    WasteCapability,
)
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.capability.waste import (
    _CATALYST_ROLES,
    _CONSUMED_ROLES,
    _SPENT_STREAM_OP_KINDS,
    _SPENT_STREAM_OP_ROLES,
    _SPENT_STREAM_ROLES,
    _name_covers,
    _resolve_hazard,
    derive_waste,
)
from smartchem.conditions import ConditionEnvelope
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.handling import Fate, verify_handling
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route
from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep, StepError
from smartchem.experiment.stock import structure_key
from smartchem.material_spec import EvidenceKind
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureOperation,
)
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.smiles import parse_smiles
from smartchem.stream_disposition import (
    DispositionValue,
    StreamDisposition,
    StreamSubject,
    SubjectKind,
    stream_subjects,
)

from tests.test_v0_9_round_v_zero_fit_theorem import (
    _ACETIC,
    _MEOAC,
    _METHANOL,
    _URL,
    _WATER,
    _dme_route,
    _maximal_profile,
    _pure,
    _use,
)
from tests.test_v0_9_round_v_zero_fit_theorem import _micro_route as _zero_fit_micro_route

_ROUTED, _CC, _RECOVERED = DispositionValue.ROUTED, DispositionValue.CONSUMED_COMPLETELY, DispositionValue.RECOVERED
_SQ = EvidenceKind.SOURCE_QUOTED
_AN, _HAZ, _OFFGAS = WasteCapability.AQUEOUS_NEUTRAL, WasteCapability.HAZARDOUS, WasteCapability.OFFGAS_CAPTURE
_SRC = SourceCitation(_URL, SourceReview.ACCEPTED)
_UNK = EvidenceField.unknown()
_AC2O = parse_smiles("CC(=O)OC(C)=O")
_H2SO4 = parse_smiles("OS(=O)(=O)O")
#: a catalyst identity + name with NO hazard record anywhere in the tables (probed): its residual is an open obligation
_UNRECORDED_CAT = parse_smiles("CC(C)(C)c1ccccc1")
_AXES = ("material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
         "procurement", "attention_care", "monetary")


# =====================================================================================================================
# the ORACLE: the pre-S10 derive_waste, frozen verbatim (tree a890e8a + the S10 vocabulary commit). It shares only the
# module's helpers and role tables, so any difference in output is a difference in the BODY this incision replaced.
# =====================================================================================================================

def _derive_waste_pre_s10(
    route: ExperimentRoute,
) -> "tuple[frozenset[WasteCapability], tuple[str, ...], tuple[str, ...]]":
    """``(categories, reasons, unresolved)`` for ``route`` under barrier D9 -- pure, route-only.

    ``reasons`` name the facts that EARNED a category; ``unresolved`` names every stream whose routing could not
    be positively determined (assess caps the waste axis at UNKNOWN on any). Both are sorted, de-duplicated.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")
    categories: "set[WasteCapability]" = set()
    reasons: "set[str]" = set()
    unresolved: "set[str]" = set()

    # -- byproducts ---------------------------------------------------------------------------------------------
    handling = verify_handling(route)
    ghs_by_name: "dict[str, tuple[str, ...]]" = {}
    for step_handling in handling.steps:
        for flag in step_handling.hazards:
            ghs_by_name.setdefault(flag.name, tuple(flag.ghs_codes))
    for b in handling.all_byproducts:
        fate = b.fate.value if isinstance(b.fate, Fate) else str(b.fate)
        label = f"byproduct {b.molecule!r} (fate={fate})"
        if b.hazard_name is None:
            unresolved.add(f"waste: {label} has NO hazard assessment -- its disposal routing is UNKNOWN, never "
                           "benign by negation (F48)")
            continue
        if b.hazard_name not in ghs_by_name:
            unresolved.add(f"waste: {label} names hazard record {b.hazard_name!r} but no GHS flag for it is "
                           "present in the handling ledger -- routing UNKNOWN")
            continue
        codes = ghs_by_name[b.hazard_name]
        if b.fate is Fate.OFFGAS:
            categories.add(WasteCapability.OFFGAS_CAPTURE)
            reasons.add(f"waste: {label} evolves as an off-gas ({b.reason}) -- needs OFFGAS_CAPTURE")
        if codes:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.add(f"waste: {label} carries sourced GHS {', '.join(codes)} ({b.hazard_name}) -- HAZARDOUS")
            if b.fate is Fate.UNKNOWN:
                unresolved.add(f"waste: {label} is hazardous ({b.hazard_name}) but its phase is UNASSESSED -- "
                               "which stream carries it is UNKNOWN")
        else:
            # F76: an empty GHS profile clears the SPECIES, never the STREAM (phase/pH/co-residents unknown).
            unresolved.add(f"waste: {label} ({b.hazard_name}, empty GHS) -- benign species, untyped waste stream "
                           "(phase/pH/co-residents unestablished); never AQUEOUS_NEUTRAL (F76)")

    # -- residuals (F77), role consistency (F-7), untyped introductions (F-6), spent streams (D9) ------------------
    catalyst_seen: "set[str]" = set()
    residual_seen: "set[str]" = set()
    stream_names_seen: "set[str]" = set()

    # F-7 pre-pass: every name a known-identity CATALYST use carries while its own step NET-CONSUMES that structure.
    # Computed before any catalyst is read, so neither the use nor a same-named envelope catalyst (read first, and
    # deduplicated by name) can ever earn the resolved catalyst category for a consumed reactant.
    contradicted: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                if (use.role in _CATALYST_ROLES and use.identity is not None
                        and step.net_consumes(use.identity)):
                    contradicted.add(use.name.strip().casefold())

    def _catalyst(identity, name: str, where: str) -> None:
        key = name.strip().casefold()
        if key in contradicted:
            unresolved.add(
                f"waste: catalyst {name!r} ({where}) is NET-CONSUMED by its step's balanced reaction -- a role "
                "contradiction, never a catalyst residual; its unreacted/excess residual's disposal routing is "
                "UNKNOWN (F-7)")
            return
        if key in catalyst_seen:
            return
        catalyst_seen.add(key)
        hazard = _resolve_hazard(identity, name)
        if hazard is not None and hazard.ghs_codes:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.add(f"waste: catalyst residual {name!r} ({where}) is not consumed and carries sourced GHS "
                        f"{', '.join(hazard.ghs_codes)} ({hazard.name}) -- HAZARDOUS")
        else:
            why = "no hazard record" if hazard is None else f"{hazard.name}, empty GHS -- benign species, untyped stream"
            unresolved.add(f"waste: catalyst residual {name!r} ({where}) is not consumed ({why}) -- its disposal "
                           "routing is UNKNOWN")

    for s_index, step in enumerate(route.steps, start=1):
        for cat in step.envelope.catalysts:
            _catalyst(None, cat, f"step {s_index} envelope catalyst")
        # Part IV: ``envelope.medium`` is condition PROSE / provenance only -- it is never read as a stream.
        procedure = step.envelope.procedure
        covered: "set[str]" = set()
        if procedure is not None:
            for op in procedure.operations:
                # F-6: an untyped material this op introduces has an untyped fate -- its own obligation, on every
                # op kind (a spent-stream op's line below names only its typed uses when it has any).
                for raw in op.materials:
                    if not any(_name_covers(u.name, raw) for u in op.material_uses):
                        unresolved.add(
                            f"waste: step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} introduces "
                            f"untyped material {raw.strip()!r} -- its fate is untyped, so its disposal routing is "
                            "UNKNOWN (F-6)")
                for use in op.material_uses:
                    if use.identity is not None:
                        covered.add(structure_key(use.identity))
                    if use.role in _CATALYST_ROLES:
                        _catalyst(use.identity, use.name, f"step {s_index} op #{op.ordinal} CATALYST use")
                        if use.identity is not None and step.net_consumes(use.identity):
                            residual_seen.add(structure_key(use.identity))
                    elif use.role in _CONSUMED_ROLES:
                        key = (structure_key(use.identity) if use.identity is not None
                               else f"name:{use.name.strip().casefold()}")
                        if key not in residual_seen:
                            residual_seen.add(key)
                            unresolved.add(
                                f"waste: unreacted/excess {use.name!r} ({use.role.value}) residual -- full "
                                "consumption or recovery is not typed, so its disposal routing is UNKNOWN (F77)")
                    if use.role in _SPENT_STREAM_ROLES:
                        nkey = use.name.strip().casefold()
                        if nkey not in stream_names_seen:
                            stream_names_seen.add(nkey)
                            unresolved.add(
                                f"waste: spent workup stream {use.name!r} ({use.role.value}) -- the sourced "
                                "procedure declares no disposal routing, so its waste handling is UNKNOWN (F49)")
                if op.role in _SPENT_STREAM_OP_ROLES or op.kind in _SPENT_STREAM_OP_KINDS:
                    if op.material_uses:
                        what = ", ".join(sorted({u.name for u in op.material_uses}))
                    elif op.materials:
                        what = ", ".join(sorted(set(op.materials)))
                    else:
                        what = "no named materials"
                    unresolved.add(
                        f"waste: step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} leaves a spent "
                        f"stream ({what}) -- no disposal routing is sourced, so it is UNKNOWN (D9)")
        # every reactant/reagent no typed use covers is an unresolved residual (no procedure => all of them).
        for molecule in tuple(step.reactants) + tuple(step.reagents):
            key = structure_key(molecule)
            if key in covered or key in residual_seen:
                continue
            residual_seen.add(key)
            unresolved.add(
                f"waste: step {s_index} input {molecule!r} has no typed procedure use -- any unreacted/excess "
                "residual's disposal routing is UNKNOWN (F77; no stoichiometry guessed)")

    return frozenset(categories), tuple(sorted(reasons)), tuple(sorted(unresolved))


# =====================================================================================================================
# fixtures
# =====================================================================================================================

@lru_cache(maxsize=1)
def _dme() -> ExperimentRoute:
    return _dme_route()


def _one(items):
    items = tuple(items)
    assert len(items) == 1, items
    return items[0]


def _dme_subjects() -> "tuple[StreamSubject, StreamSubject, StreamSubject]":
    subjects = stream_subjects(_dme().steps[0])
    water = _one(s for s in subjects if s.kind is SubjectKind.BYPRODUCT)
    op3 = _one(s for s in subjects if s.kind is SubjectKind.OP_STREAM)
    methanol = _one(s for s in subjects if s.kind is SubjectKind.RESIDUAL)
    assert op3.ordinal == 3 and water.core == structure_key(_WATER) and methanol.core == structure_key(_METHANOL)
    return water, op3, methanol


def _d(subject, value=_ROUTED, *, category=None, via_op=None, evidence=_SQ, locator=_URL) -> StreamDisposition:
    if value is _ROUTED and category is None:
        category = _AN
    return StreamDisposition(subject, value, evidence, locator, category=category, via_op=via_op)


def _forge(subject, value, *, evidence=_SQ, category=None, via_op=None) -> StreamDisposition:
    """A record that SKIPPED construction (a hand-forged object, as a buggy codec could build): the derive-time checks
    are the only thing standing between it and a discharge."""
    forged = object.__new__(StreamDisposition)
    for name, value_ in (("subject", subject), ("value", value), ("evidence", evidence), ("locator", _URL),
                         ("category", category), ("via_op", via_op)):
        object.__setattr__(forged, name, value_)
    return forged


def _with(route: ExperimentRoute, *dispositions, step: int = 0, source: "SourceCitation | None" = None):
    """``route`` with step ``step``'s procedure carrying ``dispositions`` (and optionally another source)."""
    old = route.steps[step]
    over = {"stream_dispositions": tuple(dispositions)}
    if source is not None:
        over["source"] = source
    procedure = dc.replace(old.envelope.procedure, **over)
    steps = list(route.steps)
    steps[step] = dc.replace(old, envelope=dc.replace(old.envelope, procedure=procedure))
    return ExperimentRoute(ROUTE_SCHEMA, tuple(steps))


def _witness_dispositions():
    water, op3, methanol = _dme_subjects()
    return _d(water, category=_AN), _d(op3, category=_AN), _d(methanol, _CC)


def _exact_profile(waste=frozenset({_AN})):
    """Freeze §6's exactly-sufficient Custom bench: every set is exactly what the route requires, nothing spare."""
    return dc.replace(
        _maximal_profile((_pure("methanol-pure", _METHANOL),)),
        equipment=frozenset({EquipmentCapability.CONTROLLED_HEATING, EquipmentCapability.GRAVITY_FILTRATION,
                             EquipmentCapability.REACTION_VESSEL, EquipmentCapability.REFLUX_CONDENSER}),
        containment=frozenset({ContainmentCapability.FUME_HOOD}), measurement=frozenset({MeasurementMethod.MASS}),
        waste_handling=frozenset(waste), procurement=frozenset())


def _assess(route, profile=None):
    return assess(profile if profile is not None else _exact_profile(), compile_capability_requirements(route),
                  evaluate_route(route))


def _statuses(a) -> "dict[str, CapabilityStatus]":
    return {name: getattr(a, name).status for name in _AXES}


def _sourced_step(reactants, products, target, ops, *, catalysts=()) -> ExperimentStep:
    procedure = ProcedureEvidence(reaction_scope="fixture S10 consumption", source=_SRC, scale=_UNK,
                                  operations=tuple(ops), quench=_UNK, workup_isolation=_UNK, separation=_UNK,
                                  wash=_UNK, drying=_UNK, purification=_UNK, analytical_verification=_UNK)
    kw = {}
    if catalysts:
        kw = {"catalysts": tuple(catalysts), "status": EvidenceStatus.EXPERIMENTAL,
              "provenance": "fixture: declared catalyst"}
    return ExperimentStep(STEP_SCHEMA, target, tuple(reactants), tuple(products), (),
                          ConditionEnvelope(procedure=procedure, **kw))


def _op(kind=OperationKind.ADD, role=OperationRole.OTHER, uses=(), materials=()) -> ProcedureOperation:
    """One op; its ordinal is a placeholder -- the route builders renumber every op 1..N in order."""
    return ProcedureOperation(ordinal=1, kind=kind, role=role, material_uses=tuple(uses),
                              materials=tuple(materials), locator=_URL)


_BASE_USES = (_use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL),
              _use("acetic acid", ProcedureMaterialRole.REACTANT, _ACETIC))


def _micro(*extra_ops, base_uses=_BASE_USES, catalysts=()) -> ExperimentRoute:
    """acetic acid + methanol -> methyl acetate + water on a SOURCED procedure (op #1 ADD/REACTION + ``extra_ops``)."""
    ops = (_op(role=OperationRole.REACTION, uses=base_uses),) + tuple(
        dc.replace(op, ordinal=i) for i, op in enumerate(extra_ops, start=2))
    return ExperimentRoute(ROUTE_SCHEMA, (_sourced_step((_ACETIC, _METHANOL), (_MEOAC, _WATER), _MEOAC, ops,
                                                        catalysts=catalysts),))


def _two_step(step1_uses, step2_uses=(), *, catalysts=()) -> ExperimentRoute:
    """AcOH + MeOH -> MeOAc + H2O, then MeOAc + AcOH -> Ac2O + MeOH: acetic acid is an input of BOTH steps."""
    s1 = _sourced_step((_ACETIC, _METHANOL), (_MEOAC, _WATER), _MEOAC,
                       (_op(role=OperationRole.REACTION, uses=step1_uses),), catalysts=catalysts)
    s2 = _sourced_step((_MEOAC, _ACETIC), (_AC2O, _METHANOL), _AC2O,
                       (_op(role=OperationRole.REACTION, uses=step2_uses),), catalysts=catalysts)
    return ExperimentRoute(ROUTE_SCHEMA, (s1, s2))


def _subject_of(route, kind, *, step=0, ordinal=None, index=None, core=None) -> StreamSubject:
    return _one(s for s in stream_subjects(route.steps[step]) if s.kind is kind
                and (ordinal is None or s.ordinal == ordinal) and (index is None or s.index == index)
                and (core is None or s.core == core))


# =====================================================================================================================
# the regression differential (no dispositions): byte-identical, except a strict superset on a species-repeating route
# =====================================================================================================================

def _isopentyl():
    from tests.test_v0_9_capability_fit_positive import _isopentyl_route

    return _isopentyl_route()


_NON_REPEATING = {
    "dme": lambda: _dme(),
    "zero-fit micro": lambda: _zero_fit_micro_route(),
    "micro + two same-named rinses + wash op": lambda: _micro(
        _op(uses=(_use("cold water", ProcedureMaterialRole.RINSE), _use("cold water", ProcedureMaterialRole.RINSE))),
        _op(OperationKind.SEPARATE, OperationRole.WASH, uses=(_use("brine", ProcedureMaterialRole.WASH),)),
        _op(OperationKind.ADD, OperationRole.QUENCH, materials=("ice water",))),
    "micro + envelope catalyst covered by a typed catalyst": lambda: _micro(
        _op(uses=(_use("catalyst x", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),)),
        catalysts=("catalyst x", "sulfuric acid")),
    "micro + a real-GHS typed catalyst": lambda: _micro(
        _op(uses=(_use("sulfuric acid", ProcedureMaterialRole.CATALYST, _H2SO4),))),
    "micro without a procedure": lambda: ExperimentRoute(ROUTE_SCHEMA, (ExperimentStep(
        STEP_SCHEMA, _MEOAC, (_ACETIC, _METHANOL), (_MEOAC, _WATER), (), ConditionEnvelope()),)),
    "real isopentyl route": _isopentyl,
}


@pytest.mark.parametrize("name", sorted(_NON_REPEATING))
def test_differential_no_dispositions_is_byte_identical_to_the_pre_s10_projection(name):
    route = _NON_REPEATING[name]()
    assert derive_waste(route) == _derive_waste_pre_s10(route)


def test_differential_the_oracle_is_discriminating_on_a_species_repeating_route():
    """The two-step route repeats acetic acid (typed in step 1, untyped in step 2) and the envelope catalyst: the new
    projection is a STRICT superset -- step 2's own obligations, which step 1's route-wide dedup used to hide (D-C2)."""
    route = _two_step(_BASE_USES, catalysts=("sulfuric acid",))
    new_c, new_r, new_u = derive_waste(route)
    old_c, old_r, old_u = _derive_waste_pre_s10(route)
    assert new_c == old_c
    assert set(new_r) >= set(old_r) and set(new_u) > set(old_u)
    gained = (set(new_u) - set(old_u)) | (set(new_r) - set(old_r))
    assert gained and all("step 2" in line for line in gained), gained
    assert any("step 2 input" in line and "has no typed procedure use" in line for line in set(new_u) - set(old_u))
    assert any("step 2 envelope catalyst" in line for line in set(new_r) - set(old_r))


# =====================================================================================================================
# the synthetic reachability witness (MODEL-LEVEL; see the module docstring -- not a real procedure)
# =====================================================================================================================

#: the witness's per-axis verdicts, pinned (every axis but ventilation/procurement/attention is a positive FIT).
_WITNESS_TABLE = {
    "material": CapabilityStatus.FIT, "equipment": CapabilityStatus.FIT, "physical": CapabilityStatus.FIT,
    "process": CapabilityStatus.FIT, "containment": CapabilityStatus.FIT,
    "ventilation": CapabilityStatus.NOT_APPLICABLE, "measurement": CapabilityStatus.FIT,
    "waste": CapabilityStatus.FIT, "procurement": CapabilityStatus.NOT_APPLICABLE,
    "attention_care": CapabilityStatus.NOT_APPLICABLE, "monetary": CapabilityStatus.FIT,
}


def test_witness_without_dispositions_is_the_honest_ceiling():
    a = _assess(_dme())
    assert evaluate_route(_dme()).tier == PROCESS_SPECIFIED
    assert a.waste.status is CapabilityStatus.UNKNOWN and a.overall is CapabilityStatus.UNKNOWN
    assert len(derive_waste(_dme())[2]) == 3


def test_witness_three_dispositions_reach_capability_fit_under_the_exact_bench():
    route = _with(_dme(), *_witness_dispositions())
    assert evaluate_route(route).tier == PROCESS_SPECIFIED
    cats, reasons, unresolved = derive_waste(route)
    assert cats == frozenset({_AN}) and unresolved == ()
    assert sum("(S10)" in r and "this obligation is discharged" in r for r in reasons) == 3
    a = _assess(route)
    assert _statuses(a) == _WITNESS_TABLE, _statuses(a)
    assert a.overall is CapabilityStatus.FIT and a.is_capability_fit


def test_witness_the_bench_is_exactly_sufficient():
    route = _with(_dme(), *_witness_dispositions())
    reqs, profile = compile_capability_requirements(route), _exact_profile()
    assert reqs.equipment == profile.equipment and reqs.containment == profile.containment
    assert reqs.measurement == profile.measurement and reqs.waste.categories == profile.waste_handling
    for field in ("equipment", "containment", "measurement", "waste_handling"):
        for member in getattr(profile, field):
            thinner = dc.replace(profile, **{field: getattr(profile, field) - {member}})
            assert not _assess(route, thinner).is_capability_fit, (field, member)


@pytest.mark.parametrize("dropped", [0, 1, 2], ids=["water-byproduct", "op3-filter-stream", "methanol-residual"])
def test_witness_deleting_any_one_disposition_is_unknown(dropped):
    kept = tuple(d for i, d in enumerate(_witness_dispositions()) if i != dropped)
    route = _with(_dme(), *kept)
    _cats, _reasons, unresolved = derive_waste(route)
    expected = _derive_waste_pre_s10(_dme())[2]
    assert len(unresolved) == 1 and unresolved[0] in expected
    a = _assess(route)
    assert a.waste.status is CapabilityStatus.UNKNOWN and a.overall is CapabilityStatus.UNKNOWN


def test_witness_a_bench_without_aqueous_neutral_is_blocked():
    a = _assess(_with(_dme(), *_witness_dispositions()), _exact_profile(waste=frozenset()))
    assert a.waste.status is CapabilityStatus.BLOCKED and a.overall is CapabilityStatus.BLOCKED


def test_witness_changing_the_routed_category_moves_only_the_waste_axis():
    water, op3, methanol = _dme_subjects()
    fit = _assess(_with(_dme(), *_witness_dispositions()))
    moved_route = _with(_dme(), _d(water, category=_HAZ), _d(op3, category=_AN), _d(methanol, _CC))
    moved = _assess(moved_route)
    assert moved.waste.status is CapabilityStatus.BLOCKED and moved.overall is CapabilityStatus.BLOCKED
    assert all(getattr(moved, n) == getattr(fit, n) for n in _AXES if n != "waste")
    assert _assess(moved_route, _exact_profile(waste=frozenset({_AN, _HAZ}))).is_capability_fit


def test_witness_a_disposition_never_discharges_another_subject():
    """Swapping A's disposition onto B: INERT when it stays on a real subject (no leak), REFUSED when the re-pointed
    subject is illegal or does not exist in this step (never a silent rebind)."""
    water, op3, methanol = _dme_subjects()
    # inert: the byproduct's ROUTED(AQUEOUS_NEUTRAL) does not also settle the op #3 stream carrying the same category
    _c, _r, unresolved = derive_waste(_with(_dme(), _d(water), _d(methanol, _CC)))
    assert len(unresolved) == 1 and "op #3 FILTER/OTHER leaves a spent stream" in unresolved[0]
    # refused (L2): methanol's CONSUMED_COMPLETELY re-pointed onto the water byproduct
    with pytest.raises(ValueError, match="L2"):
        _d(water, _CC)
    # refused (binding): op #3's ROUTED re-pointed onto op #4 (VERIFY -- not a spent-stream op) with op #3's core
    with pytest.raises(StepError, match="does not exist in this step"):
        _with(_dme(), _d(dc.replace(op3, ordinal=4)))
    # refused (binding): the same statement carried onto another reaction that also yields water
    with pytest.raises(StepError, match="reaction signature"):
        _with(_micro(), _d(water))


@pytest.mark.parametrize("evidence", [k for k in EvidenceKind if k is not EvidenceKind.SOURCE_QUOTED],
                         ids=lambda k: k.value)
def test_witness_non_certifying_evidence_is_refused_at_construction_and_discharges_nothing_if_forged(evidence):
    water, op3, methanol = _dme_subjects()
    with pytest.raises(ValueError, match="SOURCE_QUOTED"):
        _d(water, evidence=evidence)
    route = _with(_dme(), _forge(water, _ROUTED, evidence=evidence, category=_AN), _d(op3), _d(methanol, _CC))
    _cats, _r, unresolved = derive_waste(route)
    assert any("empty GHS" in u for u in unresolved)  # the forged statement settled nothing
    assert any("discharges nothing" in u and "cannot certify" in u for u in unresolved)
    assert not _assess(route).is_capability_fit


def test_witness_an_unaccepted_procedure_source_discharges_nothing():
    route = _with(_dme(), *_witness_dispositions(), source=SourceCitation(_URL, SourceReview.UNREVIEWED))
    cats, reasons, unresolved = derive_waste(route)
    assert cats == frozenset() and not any("(S10)" in r for r in reasons)
    assert set(_derive_waste_pre_s10(_dme())[2]) <= set(unresolved)
    assert sum("not an ACCEPTED citation" in u for u in unresolved) == 3
    assert not _assess(route).is_capability_fit


# =====================================================================================================================
# L1 in isolation: one for one, monotone, admissible values, via_op, L3, fate
# =====================================================================================================================

def test_l1_one_disposition_discharges_exactly_one_obligation():
    """Two differently-named CATALYST uses of ONE unrecorded species are two catalyst-residual obligations on ONE
    RESIDUAL subject. One RECOVERED statement settles one of them; the other stays open and says why."""
    route = _micro(_op(uses=(_use("catalyst x", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),
                                _use("catalyst y", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT))),
                   _op(OperationKind.FILTER))
    before = [u for u in derive_waste(route)[2] if "catalyst residual" in u]
    assert len(before) == 2
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_UNRECORDED_CAT))
    _c, reasons, unresolved = derive_waste(_with(route, _d(residual, _RECOVERED, via_op=3)))
    assert sum("catalyst residual" in r and "(S10)" in r for r in reasons) == 1
    assert sum(u in before for u in unresolved) == 1
    assert any("already discharged one obligation" in u for u in unresolved)


def test_l1_a_disposition_never_deletes_a_derived_category():
    route = _micro(_op(uses=(_use("sulfuric acid", ProcedureMaterialRole.CATALYST, _H2SO4),)),
                   _op(OperationKind.FILTER))
    cats0 = derive_waste(route)[0]
    assert _HAZ in cats0  # a real-GHS catalyst residual is a RESOLVED category, not an obligation
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_H2SO4))
    recovered = derive_waste(_with(route, _d(residual, _RECOVERED, via_op=3)))
    assert recovered[0] == cats0 and any("the derived HAZARDOUS stays" in r for r in recovered[1])
    routed = derive_waste(_with(route, _d(residual, category=_AN)))
    assert routed[0] == cats0 | {_AN}  # unioned, never swapped


def test_l1_consumed_completely_on_a_byproduct_discharges_nothing_even_when_forged():
    water, _op3, _methanol = _dme_subjects()
    _c, _r, unresolved = derive_waste(_with(_dme(), _forge(water, _CC)))
    assert any("empty GHS" in u for u in unresolved)
    assert any("CONSUMED_COMPLETELY cannot discharge this obligation" in u for u in unresolved)


def test_l1_recovered_without_a_real_recovery_op_discharges_nothing_even_when_forged():
    route = _micro(_op(uses=(_use("brine", ProcedureMaterialRole.WASH),)))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    _c, _r, unresolved = derive_waste(_with(route, _forge(stream, _RECOVERED, via_op=None)))
    assert any("spent workup stream 'brine'" in u for u in unresolved)
    assert any("names no DISTILL/FILTER/SEPARATE" in u for u in unresolved)


def test_l1_recovered_discharges_the_use_stream_but_never_the_recovering_op_stream():
    route = _micro(_op(uses=(_use("brine", ProcedureMaterialRole.WASH),)), _op(OperationKind.FILTER))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    _c, reasons, unresolved = derive_waste(_with(route, _d(stream, _RECOVERED, via_op=3)))
    assert not any("spent workup stream 'brine'" in u for u in unresolved)
    assert any("op #3 FILTER/OTHER leaves a spent stream" in u for u in unresolved)
    assert any("RECOVERED via op #3" in r for r in reasons)


def test_l1_consumed_completely_discharges_a_net_consumed_residual():
    route = _micro()
    methanol = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_METHANOL))
    _c, _r, unresolved = derive_waste(_with(route, _d(methanol, _CC)))
    assert not any("'methanol' (SUBSTRATE)" in u for u in unresolved)
    assert any("'acetic acid' (REACTANT)" in u for u in unresolved)


def test_l3_a_species_level_routed_needs_a_hazard_record(monkeypatch):
    import smartchem.capability.waste as waste_mod

    real = verify_handling(_dme())
    step_handling = real.steps[0]
    unassessed = tuple(dc.replace(b, hazard_name=None) for b in step_handling.byproducts)
    forged = dc.replace(real, steps=(dc.replace(step_handling, byproducts=unassessed),))
    monkeypatch.setattr(waste_mod, "verify_handling", lambda route, **kw: forged)
    water, op3, methanol = _dme_subjects()
    _c, _r, unresolved = derive_waste(_with(_dme(), *_witness_dispositions()))
    assert any("NO hazard assessment" in u for u in unresolved)
    assert any("no hazard record" in u and "(L3)" in u for u in unresolved)


def test_a_fate_contradiction_stays_unknown_never_blocked():
    water, op3, methanol = _dme_subjects()
    route = _with(_dme(), _d(water, category=_OFFGAS), _d(op3), _d(methanol, _CC))
    cats, _r, unresolved = derive_waste(route)
    assert _OFFGAS not in cats
    assert any("contradicts the derived CONDENSED fate" in u for u in unresolved)
    a = _assess(route)  # the exact bench lacks OFFGAS_CAPTURE: a counted category would BLOCK; a refused one cannot
    assert a.waste.status is CapabilityStatus.UNKNOWN and a.overall is CapabilityStatus.UNKNOWN


# =====================================================================================================================
# the latent defects: D-C1 (per-use streams), D-C2 (per-step dedup), D-C4 (envelope catalyst attribution), exclusions
# =====================================================================================================================

def test_dc1_two_same_named_use_streams_are_two_obligations():
    route = _micro(_op(uses=(_use("cold water", ProcedureMaterialRole.RINSE),
                                _use("cold water", ProcedureMaterialRole.RINSE))))
    first = _subject_of(route, SubjectKind.USE_STREAM, index=0)
    second = _subject_of(route, SubjectKind.USE_STREAM, index=1)
    marker = "spent workup stream 'cold water'"
    assert any(marker in u for u in derive_waste(_with(route, _d(first)))[2])   # the second stream is still open
    assert any(marker in u for u in derive_waste(_with(route, _d(second)))[2])  # ...and vice versa
    assert not any(marker in u for u in derive_waste(_with(route, _d(first), _d(second)))[2])


def test_dc2_a_step_one_residual_never_answers_for_step_two():
    route = _two_step(_BASE_USES)
    acetic1 = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_ACETIC))
    _c, reasons, unresolved = derive_waste(_with(route, _d(acetic1, _CC)))
    assert any("step 1 residual 'acetic acid'" in r for r in reasons)
    assert any("step 2 input" in u and "has no typed procedure use" in u and repr(_ACETIC) in u for u in unresolved)


def test_dc4_an_envelope_catalyst_is_attributed_to_its_covering_typed_use():
    route = _micro(_op(uses=(_use("catalyst x", ProcedureMaterialRole.CATALYST, _UNRECORDED_CAT),)),
                   _op(OperationKind.FILTER), catalysts=("Catalyst X",))
    before = derive_waste(route)[2]
    assert any("'Catalyst X' (step 1 envelope catalyst)" in u for u in before)
    assert not any("CATALYST use" in u for u in before)  # the typed use is the SAME residual (name-deduplicated)
    residual = _subject_of(route, SubjectKind.RESIDUAL, core=structure_key(_UNRECORDED_CAT))
    _c, reasons, unresolved = derive_waste(_with(route, _d(residual, _RECOVERED, via_op=3)))
    assert not any("catalyst residual 'Catalyst X'" in u and "not consumed" in u for u in unresolved)
    assert any("catalyst residual 'Catalyst X' (step 1 envelope catalyst)" in r and "(S10)" in r for r in reasons)


def test_dc4_an_uncovered_envelope_catalyst_has_no_subject_at_all():
    route = _micro(catalysts=("catalyst x",))
    residual_cores = {s.core for s in stream_subjects(route.steps[0]) if s.kind is SubjectKind.RESIDUAL}
    assert residual_cores == {structure_key(_METHANOL), structure_key(_ACETIC)}  # nothing a statement could name
    assert any("'catalyst x' (step 1 envelope catalyst)" in u for u in derive_waste(route)[2])


def test_excluded_kinds_survive_every_discharge():
    """Untyped op material has no subject: with all three witness subjects discharged it still holds waste open."""
    base = _dme()
    step = base.steps[0]
    ops = list(step.envelope.procedure.operations)
    ops[0] = dc.replace(ops[0], materials=ops[0].materials + ("mystery salt",))
    procedure = dc.replace(step.envelope.procedure, operations=tuple(ops))
    route = ExperimentRoute(ROUTE_SCHEMA, (dc.replace(step, envelope=dc.replace(step.envelope, procedure=procedure)),))
    water = _subject_of(route, SubjectKind.BYPRODUCT)
    op3 = _subject_of(route, SubjectKind.OP_STREAM)
    methanol = _subject_of(route, SubjectKind.RESIDUAL)
    assert not any("mystery" in s.core for s in stream_subjects(route.steps[0]))
    _c, _r, unresolved = derive_waste(_with(route, _d(water), _d(op3), _d(methanol, _CC)))
    assert len(unresolved) == 1 and "introduces untyped material 'mystery salt'" in unresolved[0]


# =====================================================================================================================
# the corpus: no cited page states disposal, so no production envelope carries a disposition
# =====================================================================================================================

def test_no_corpus_procedure_carries_a_stream_disposition():
    procedures = [v for v in vars(decompiler_conditions).values() if type(v) is ProcedureEvidence]
    assert len(procedures) >= 3
    assert all(p.stream_dispositions == () for p in procedures)

