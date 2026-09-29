"""Round V X-high (Part VII): the ZERO-FIT THEOREM, pinned -- and the proof that it is a missing EVIDENCE TYPE, not an
overconstrained evaluator.

**Wubba lubba dub dub, the verdict word nobody can say.** The corpus has no ``CAPABILITY_FIT``. That is not graded as a
defect -- but a verdict word the implementation can NEVER return, even in a fully-specified synthetic world, would be.
So this file pins BOTH halves:

* **The theorem (every route, not just the corpus).** For every ``ExperimentRoute`` and every profile, the waste axis
  can never be FIT/NOT_APPLICABLE, hence overall is never ``CAPABILITY_FIT``. Independent guards, each sufficient:
  - **T0 (spent stream)** -- PROCESS_SPECIFIED requires ``workup_isolation`` PRESENT; the coherence guard then
    requires an op that realizes it; EVERY workup-realizing (kind x role) pair yields an unresolved D9 spent-stream
    obligation (exhaustive over the closed enums, below);
  - **T1 (leaf complementarity)** -- every consumed leaf either carries a SUBSTRATE/REACTANT use (an unresolved
    "unreacted/excess" residual), a role contradiction (F-7), a spent-stream role, or keeps its ``UNKNOWN`` leaf demand
    on the MATERIAL axis (never EXACT); no typed role launders a consumed leaf out of both axes;
  - **T2 (byproducts)** -- an empty-GHS byproduct (the water of every condensation) is an untyped stream.
  No branch of ``derive_waste`` reads any disposition / recovery / full-consumption evidence: the ceiling is a missing
  evidence TYPE (``StreamDisposition``, parked to 0.9.5), never missing data.
* **The witness (the evaluator is not overconstrained).** A REAL ``PROCESS_SPECIFIED`` route (2 MeOH -> dimethyl
  ether + water, the real capped-scission transform, a sourced complete procedure typed so every D14-D18 law is
  satisfied) is FIT on every axis except waste under a fully-declared bench; its compiled requirements with ONLY the
  waste obligation discharged fold to overall ``CAPABILITY_FIT``. So FIT is reachable the moment the evidence
  vocabulary can say where the streams go -- and nowhere earlier.
"""
from __future__ import annotations

import dataclasses as dc

import pytest

from smartchem.capability.assess import assess
from smartchem.capability.coverage import render_scale, render_summary, render_verification
from smartchem.capability.enums import (
    CapabilityStatus,
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    WasteCapability,
)
from smartchem.capability.presets import custom
from smartchem.capability.quantity import QuantityKnowledge
from smartchem.capability.requirements import WasteRequirement, compile_capability_requirements
from smartchem.capability.waste import derive_waste
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.contracts import EvidenceStatus
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.data.reagents import Availability
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route
from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MaterialComponent, Phase, StockMaterial, StockQuantity
from smartchem.material_spec import ConcentrationBasis, EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
    _field_matches,
)
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import CappedScissionProvider

_METHANOL, _ACETIC, _WATER = parse_smiles("CO"), parse_smiles("CC(=O)O"), parse_smiles("O")
_MEOAC, _DME = parse_smiles("CC(=O)OC"), parse_smiles("COC")
_UNK = EvidenceField.unknown()
_URL = "https://example.test/synthetic-zero-fit-witness"
_SRC = SourceCitation(_URL, SourceReview.ACCEPTED)
_SQ_LIQUID = PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED)
_SAFE_STATUSES = (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)


def _use(name, role, identity=None, qty="10"):
    return ProcedureMaterialUse(name=name, role=role, identity=identity, phase=_SQ_LIQUID,
                                quantity=None if qty is None else StockQuantity.of(qty, "mL"),
                                evidence_source="fixture zero-fit theorem")


def _micro_route(*, base_uses=None, extra_ops=()) -> ExperimentRoute:
    """acetic acid + methanol -> methyl acetate + water, one real conserving step, procedure evidence attached."""
    base_uses = base_uses if base_uses is not None else (
        _use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL),
        _use("acetic acid", ProcedureMaterialRole.REACTANT, _ACETIC))
    op1 = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                             material_uses=tuple(base_uses), locator="fixture")
    ops = (op1,) + tuple(dc.replace(op, ordinal=i) for i, op in enumerate(extra_ops, start=2))
    procedure = ProcedureEvidence(reaction_scope="fixture", source=None, scale=_UNK, operations=ops, quench=_UNK,
                                  workup_isolation=_UNK, separation=_UNK, wash=_UNK, drying=_UNK, purification=_UNK,
                                  analytical_verification=_UNK)
    step = ExperimentStep(STEP_SCHEMA, _MEOAC, (_ACETIC, _METHANOL), (_MEOAC, _WATER), (),
                          ConditionEnvelope(procedure=procedure))
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


def _pure(mid: str, molecule) -> StockMaterial:
    ev = IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="fixture: the bench declares its own bottle pure")
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, (MaterialComponent.evidenced(molecule, "active", ev),),
                         Phase.LIQUID, "fixture", quantity=StockQuantity.of("500", "mL"),
                         phase_evidence=EvidenceKind.USER_DECLARED)


def _maximal_profile(inventory) -> "object":
    """Every capability the model can express, fully DECLARED (never an all-None 'unlimited' strawman)."""
    return custom(
        profile_id="zero-fit-maximal", material_inventory=tuple(inventory), equipment=frozenset(EquipmentCapability),
        physical_bounds=PhysicalBounds.of(max_temperature_k=600.0, min_pressure_atm=0.5, max_pressure_atm=5.0,
                                          min_temperature_k=250.0),
        process_bounds=ProcessBounds.of(max_step_minutes=600.0, max_total_minutes=600.0, max_active_minutes=600.0,
                                        allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                                        allowed_agitation=tuple(Agitation)),
        containment=frozenset(ContainmentCapability), measurement=frozenset(MeasurementMethod),
        waste_handling=frozenset(WasteCapability), procurement=frozenset(Availability),
        no_limit_dimensions=frozenset({"budget"}))


# -- T0: every workup-realizing operation yields an unresolved spent stream (exhaustive over the closed enums) -------

_WORKUP_REALIZING = [(k, r) for k in OperationKind for r in OperationRole
                     if _field_matches(None, "workup_isolation", ProcedureOperation(
                         ordinal=1, kind=k, role=r, locator="probe"))]


def test_t0_the_workup_realizing_set_is_nonempty_and_closed():
    kinds = {k for k, _r in _WORKUP_REALIZING}
    assert {OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY} <= kinds
    assert any(r is OperationRole.WASH for _k, r in _WORKUP_REALIZING)


@pytest.mark.parametrize("kind,role", _WORKUP_REALIZING, ids=lambda x: x.value)
def test_t0_every_workup_realizing_op_leaves_an_unresolved_spent_stream(kind, role):
    op = ProcedureOperation(ordinal=2, kind=kind, role=role, locator="probe")
    _cats, _reasons, unresolved = derive_waste(_micro_route(extra_ops=(op,)))
    assert any("op #2" in u and "spent stream" in u for u in unresolved), (kind, role, unresolved)


# -- T1: leaf complementarity -- no typed role launders a consumed leaf out of BOTH the waste and material axes -------

@pytest.mark.parametrize("role", list(ProcedureMaterialRole), ids=lambda r: r.value)
def test_t1_a_consumed_leaf_under_any_typed_role_keeps_an_open_obligation(role):
    uses = (_use("methanol", role, _METHANOL), _use("acetic acid", ProcedureMaterialRole.REACTANT, _ACETIC))
    route = _micro_route(base_uses=uses)
    _cats, _reasons, unresolved = derive_waste(route)
    reqs = compile_capability_requirements(route)
    waste_open = any("methanol" in u for u in unresolved)
    material_open = any(r.identity is not None and r.identity.canonical() == _METHANOL.canonical()
                        and (r.quantity.knowledge is not QuantityKnowledge.EXACT or r.specification.unresolved_terms)
                        for r in reqs.material)
    assert waste_open or material_open, (role, unresolved)
    profile = _maximal_profile((_pure("methanol-pure", _METHANOL), _pure("acetic-pure", _ACETIC)))
    a = assess(profile, reqs, evaluate_route(route))
    assert a.overall is not CapabilityStatus.FIT


# -- T2: an empty-GHS byproduct is a benign SPECIES in an untyped STREAM -----------------------------------------------

def test_t2_the_water_byproduct_is_an_untyped_stream_never_aqueous_neutral():
    cats, _reasons, unresolved = derive_waste(_micro_route())
    assert WasteCapability.AQUEOUS_NEUTRAL not in cats
    assert any("empty GHS" in u and "untyped waste stream" in u for u in unresolved)


# -- the evaluator-reachability witness ---------------------------------------------------------------------------------

def _dme_route() -> ExperimentRoute:
    """2 MeOH -> dimethyl ether + water: the REAL capped-scission transform (a real ReactionCenter), a SOURCED complete
    procedure whose every stated demand is TYPED (temperatures and durations are Intervals, apparatus is kind-
    admissible, the VERIFY op names its instrument, no prose rate/agitation/endpoint), a fully-declared process record.
    X-high D24.1: every PRESENT summary field (scale, workup/isolation, analytical verification) is the CANONICAL
    rendering of its typed carriers (``coverage.render_*``) -- prose would be an unread demand -- and the filtration is
    GRAVITY (a vacuum op would contradict the record's 1 atm whole-step minimum)."""
    transforms, _receipt = CappedScissionProvider().enumerate_transforms(_DME, (_WATER,), budget=50_000)
    transform = next(t for t in transforms if all(str(p) == str(_METHANOL) for p in t.products))
    na = lambda why: EvidenceField.not_applicable(_URL, why)  # noqa: E731 -- a local constructor alias
    ops = (
        ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, materials=("methanol",),
                           material_uses=(_use("methanol", ProcedureMaterialRole.SUBSTRATE, _METHANOL, qty="20"),),
                           apparatus=("100-mL round-bottom flask",), locator=_URL),
        ProcedureOperation(ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION,
                           temperature=EvidenceField.present(Interval(330.0, 330.0, "K"), _URL),
                           duration=EvidenceField.present(Interval(30.0, 30.0, "min"), _URL),
                           apparatus=("reflux condenser", "heating mantle"), locator=_URL),
        ProcedureOperation(ordinal=3, kind=OperationKind.FILTER, role=OperationRole.OTHER,
                           apparatus=("fluted filter paper",), locator=_URL),
        ProcedureOperation(ordinal=4, kind=OperationKind.VERIFY, role=OperationRole.OTHER,
                           apparatus=("analytical balance",), locator=_URL),
    )
    draft = ProcedureEvidence(
        reaction_scope="synthetic zero-fit witness (a model-consistency object, not production chemistry)",
        source=_SRC, scale=EvidenceField.present("draft", _URL), operations=ops, quench=na("no quench"),
        workup_isolation=EvidenceField.present("draft", _URL), separation=na("no separation"), wash=na("no wash"),
        drying=na("no drying"), purification=na("no purification"),
        analytical_verification=EvidenceField.present("draft", _URL))
    procedure = dc.replace(
        draft, scale=EvidenceField.present(render_scale(draft), _URL),
        workup_isolation=EvidenceField.present(render_summary(draft, "workup_isolation"), _URL),
        analytical_verification=EvidenceField.present(render_verification(draft), _URL))
    process = ProcessRequirements(
        elapsed_minutes=Interval(30.0, 60.0, "min"), active_minutes=Interval(5.0, 10.0, "min"),
        attention=Attention.PERIODIC, check_interval_minutes=15.0, agitation=Agitation.MANUAL, workup_included=True,
        provenance="synthetic witness", source=_SRC, peak_temperature_k=330.0, min_pressure_atm=1.0,
        max_pressure_atm=1.0)
    envelope = ConditionEnvelope(temperature=Interval(330.0, 330.0, "K"), status=EvidenceStatus.EXPERIMENTAL,
                                 provenance="synthetic witness", source=_SRC, process=process, procedure=procedure)
    return ExperimentRoute(ROUTE_SCHEMA, (ExperimentStep.from_transform(transform, envelope=envelope),))


def _axis_statuses(a) -> "dict[str, CapabilityStatus]":
    return {name: getattr(a, name).status for name in (
        "material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
        "procurement", "attention_care", "monetary")}


def test_witness_the_real_dme_route_is_process_specified_and_fit_on_every_axis_but_waste():
    route = _dme_route()
    readiness = evaluate_route(route)
    assert readiness.tier == PROCESS_SPECIFIED
    a = assess(_maximal_profile((_pure("methanol-pure", _METHANOL),)), compile_capability_requirements(route), readiness)
    statuses = _axis_statuses(a)
    open_axes = {name: s for name, s in statuses.items() if s not in _SAFE_STATUSES}
    assert open_axes == {"waste": CapabilityStatus.UNKNOWN}, (open_axes, {n: getattr(a, n).reasons for n in open_axes})
    assert a.overall is CapabilityStatus.UNKNOWN


def test_witness_discharging_only_waste_reaches_capability_fit_the_evaluator_is_not_overconstrained():
    """The DISCHARGE is what 0.9 cannot express from evidence (a typed disposition vocabulary is the 0.9.5 boundary);
    here it is supplied as a public ``WasteRequirement`` value -- no law is weakened, no production code is patched."""
    route = _dme_route()
    readiness = evaluate_route(route)
    reqs = compile_capability_requirements(route)
    assert reqs.waste.unresolved  # the honest ceiling: T0 (FILTER stream), T1 (methanol residual), T2 (water)
    discharged = dc.replace(reqs, waste=WasteRequirement(frozenset(), (), ()))
    a = assess(_maximal_profile((_pure("methanol-pure", _METHANOL),)), discharged, readiness)
    assert a.overall is CapabilityStatus.FIT and a.is_capability_fit
    assert all(s in _SAFE_STATUSES for s in _axis_statuses(a).values())
