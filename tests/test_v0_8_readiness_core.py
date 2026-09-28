"""v0.8 Real Route Dossiers -- acceptance for the pure readiness-obligation core (Writer 1's file).

Cool, cool, so this pins the thing that stops the coarse tier from lying to anyone: obligations
are the source of truth, the tier is just their conservative cumulative shadow, and a step being
GREAT on one axis (sourced conditions) never bleeds into another axis it didn't earn (reaction
type). Every case below is built from a REAL, live-search-produced ``ExperimentStep`` -- no hand-
waved envelopes standing in for the corpus -- except the two cases the plan explicitly allows a
constructed record for (the declared-but-unsourced negative control and the identity-loss
blocker), which are genuinely synthetic by design (the corpus doesn't happen to carry either).
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.diels_alder import DielsAlderProvider
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.readiness import (
    CONDITIONS_SUPPORTED,
    FORMAL_CANDIDATE,
    PROCESS_SPECIFIED,
    REACTION_VOUCHED,
    ObligationStatus,
    RouteReadiness,
    StepReadiness,
    evaluate_route,
    evaluate_step,
    procedure_representation_is_complete,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.identity import stereo_loss
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry


def _mol(name: str):
    structure = structure_by_name(name)
    assert structure is not None, f"expected {name!r} in the structure registry"
    return structure.molecule


# --- corpus helpers (real search, matching plan Sec 9's forcing corpus) --------------------------

def _methyl_salicylate_step() -> ExperimentStep:
    """Row 5: recognized + sourced conditions, but the source is a qualitative smell-test with NO
    preparative procedure -> no ProcedureEvidence -> the clean CONDITIONS_SUPPORTED ceiling."""
    result = search_routes(
        _mol("methyl salicylate"), reagents=(_mol("water"), _mol("methanol")),
        available=(_mol("salicylic acid"),), max_depth=1,
    )
    assert len(result.routes) == 1 and len(result.routes[0].steps) == 1
    return result.routes[0].steps[0]


def _isopentyl_acetate_step() -> ExperimentStep:
    """0.8 Round II positive: recognized + sourced conditions + a COMPLETE, sourced ProcedureEvidence
    -> the real PROCESS_SPECIFIED route."""
    result = search_routes(
        _mol("isopentyl acetate"), reagents=(_mol("water"), _mol("acetic acid")),
        available=(_mol("isopentyl alcohol"),), max_depth=1,
    )
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return step
    raise AssertionError("expected a sourced isopentyl-acetate step carrying procedure evidence")


def _paracetamol_anhydride_step():
    """Row 2: the non-monotonic exemplar -- sourced + workup-described, but reaction-type UNRECOGNIZED
    (anhydride transacylation emits acetic acid, not water; outside the 17-class oracle)."""
    result = search_routes(
        _mol("paracetamol"), reagents=(_mol("water"), _mol("acetic acid")),
        available=(_mol("4-aminophenol"),), max_depth=2,
    )
    sourced_two_step = next(
        r for r in result.routes if len(r.steps) == 2 and r.steps[1].envelope.is_sourced
    )
    return sourced_two_step.steps[1]


def _diels_alder_step() -> ExperimentStep:
    """Row 1: recognized, no declared envelope -> REACTION_VOUCHED with conditions UNKNOWN."""
    reg = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))
    result = search_routes(
        parse_smiles("C1CC=CCC1"), reagents=(), available=(parse_smiles("C=CC=C"), parse_smiles("C=C")),
        registry=reg, max_depth=2,
    )
    assert len(result.routes) == 1
    return result.routes[0].steps[0]


def _declared_unsourced_step() -> ExperimentStep:
    """A synthetic declared-but-unsourced envelope (the corpus's built-in negative-control shape,
    e.g. ketene acetylation's ``source=None`` -- constructed directly here so the test does not
    depend on which live search path happens to surface it)."""
    envelope = ConditionEnvelope(
        temperature=Interval(300.0, 320.0, "K"),
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="a free-text lab notebook entry, never reviewed or accepted as a citation",
        source=None,
    )
    return ExperimentStep.assembling(
        parse_smiles("CC(=O)OC"), (parse_smiles("CC(=O)O"), parse_smiles("CO")),
        (parse_smiles("CC(=O)OC"), parse_smiles("O")), envelope=envelope,
    )


# --- ObligationStatus / basic construction --------------------------------------------------------

def test_obligation_status_is_its_own_enum_not_reused():
    from smartchem.contracts import EvidenceStatus as _ES

    assert set(ObligationStatus) != set(_ES)
    assert {s.value for s in ObligationStatus} == {"SATISFIED", "UNSATISFIED", "UNKNOWN", "NOT_APPLICABLE"}


# --- row 5: methyl salicylate -----------------------------------------------------------------

def test_methyl_salicylate_is_conditions_supported_with_unknown_process_and_workup():
    step = _methyl_salicylate_step()
    readiness = evaluate_step(step)
    assert readiness.formal_candidate is ObligationStatus.SATISFIED
    assert readiness.reaction_type is ObligationStatus.SATISFIED
    assert readiness.reaction_class_name == recognize_reaction_type(step)
    assert readiness.conditions is ObligationStatus.SATISFIED
    # the source carries no preparative procedure (only a qualitative detection) -> no ProcedureEvidence.
    assert step.envelope.procedure is None
    assert readiness.process is ObligationStatus.UNKNOWN
    assert readiness.workup_isolation is ObligationStatus.UNKNOWN
    assert readiness.tier == CONDITIONS_SUPPORTED  # capped by process, exactly the sourced-but-incomplete control
    assert readiness.provenance  # the accepted source locator backing conditions=SATISFIED
    assert any("workup_isolation" in o for o in readiness.open_obligations)


# --- row 2: the non-monotonicity exemplar (paracetamol + acetic anhydride) --------------------

def test_paracetamol_anhydride_step_is_non_monotonic_load_bearing_orthogonality():
    step = _paracetamol_anhydride_step()
    readiness = evaluate_step(step)
    # the load-bearing assertion: BOTH must hold at once.
    assert readiness.conditions is ObligationStatus.SATISFIED
    assert readiness.reaction_type is ObligationStatus.UNSATISFIED
    assert readiness.reaction_class_name is None
    # the coarse tier is capped by the weaker axis -- conditions being SATISFIED does not leak upward.
    assert readiness.tier == FORMAL_CANDIDATE
    assert any("reaction_type" in o for o in readiness.open_obligations)
    # 0.8 Round II, one rung higher: this step now carries a COMPLETE, SOURCED procedure, so BOTH
    # process AND workup_isolation are visibly SATISFIED -- yet the coarse tier is STILL FORMAL_CANDIDATE
    # because reaction_type is unrecognized. Richer evidence, unmoved tier: the non-monotonicity, sharpened.
    assert readiness.process is ObligationStatus.SATISFIED
    assert readiness.workup_isolation is ObligationStatus.SATISFIED
    assert readiness.provenance  # conditions=SATISFIED and the procedure's own citation


# --- row 1: Diels-Alder (reaction-vouched, conditions unknown) ---------------------------------

def test_diels_alder_step_is_reaction_vouched_with_unknown_conditions():
    step = _diels_alder_step()
    readiness = evaluate_step(step)
    assert readiness.reaction_type is ObligationStatus.SATISFIED
    assert readiness.reaction_class_name is not None
    assert readiness.conditions is ObligationStatus.UNKNOWN
    assert readiness.process is ObligationStatus.UNKNOWN
    assert readiness.workup_isolation is ObligationStatus.UNKNOWN
    assert readiness.tier == REACTION_VOUCHED
    assert not readiness.provenance  # nothing SATISFIED-and-sourced to cite


# --- declared-but-unsourced negative control ----------------------------------------------------

def test_declared_but_unsourced_envelope_is_conditions_unsatisfied():
    step = _declared_unsourced_step()
    readiness = evaluate_step(step)
    assert step.envelope.is_declared and not step.envelope.is_sourced
    assert readiness.conditions is ObligationStatus.UNSATISFIED
    assert readiness.tier == FORMAL_CANDIDATE  # esterification is recognized, but that's not this test's point
    assert any("conditions" in o for o in readiness.open_obligations)


# --- identity-loss blocker on conditions --------------------------------------------------------

def test_identity_loss_blocks_conditions_even_on_a_sourced_envelope():
    step = _methyl_salicylate_step()
    assert step.envelope.is_sourced  # sanity: without the loss this axis would be SATISFIED (prior test pins it)
    loss = stereo_loss("CC(=O)Oc1ccccc1O", double_bond=False)
    assert "conditions" in loss.affected_claims and loss.blocks("conditions")
    readiness = evaluate_step(step, identity_losses=(loss,))
    assert readiness.conditions is not ObligationStatus.SATISFIED
    assert readiness.conditions is ObligationStatus.UNSATISFIED
    assert any("blocked by identity loss" in o for o in readiness.open_obligations)
    # the tier does not rise above FORMAL_CANDIDATE because conditions is now blocked too (on top of
    # reaction_type already being UNSATISFIED for the fictional-loss target used here is irrelevant --
    # what matters is conditions itself is no longer SATISFIED).
    assert readiness.tier != CONDITIONS_SUPPORTED


def test_identity_loss_with_no_conditions_claim_does_not_block():
    step = _methyl_salicylate_step()
    # stereo_loss DOES name "conditions" (the real-world shape, pinned above) -- to exercise the "no match"
    # branch we need a loss whose affected_claims is disjoint from "conditions", so hand-build one.
    from smartchem.identity import IDENTITY_LOSS_SCHEMA, IdentityLoss, LossSeverity

    disjoint = IdentityLoss(
        IDENTITY_LOSS_SCHEMA, "isotope-labeling", "x", "constitution only (CONSTITUTION layer)",
        "an isotope label was declared but not represented", ("isotope-identity",), LossSeverity.BLOCKER,
    )
    assert not disjoint.blocks("conditions")  # sanity: this loss is genuinely orthogonal to conditions
    readiness = evaluate_step(step, identity_losses=(disjoint,))
    assert readiness.conditions is ObligationStatus.SATISFIED


# --- RouteReadiness weakest-link aggregation ----------------------------------------------------

def test_route_readiness_tier_is_the_min_over_steps():
    strong = evaluate_step(_methyl_salicylate_step())     # CONDITIONS_SUPPORTED
    weak = evaluate_step(_diels_alder_step())              # REACTION_VOUCHED
    assert strong.tier == CONDITIONS_SUPPORTED
    assert weak.tier == REACTION_VOUCHED
    route_readiness = RouteReadiness(per_step=(strong, weak), route_open_obligations=weak.open_obligations)
    assert route_readiness.tier == REACTION_VOUCHED  # the weaker step caps the whole route
    # order must not matter -- min is symmetric.
    flipped = RouteReadiness(per_step=(weak, strong), route_open_obligations=weak.open_obligations)
    assert flipped.tier == REACTION_VOUCHED


def test_evaluate_route_aggregates_a_real_two_step_route_by_min():
    result = search_routes(
        _mol("paracetamol"), reagents=(_mol("water"), _mol("acetic acid")),
        available=(_mol("4-aminophenol"),), max_depth=2,
    )
    two_step = next(r for r in result.routes if len(r.steps) == 2)
    route_readiness = evaluate_route(two_step)
    assert len(route_readiness.per_step) == 2
    from smartchem.experiment.readiness import min_tier

    assert route_readiness.tier == min_tier(sr.tier for sr in route_readiness.per_step)
    assert route_readiness.route_open_obligations
    assert route_readiness.route_open_obligations == tuple(
        sorted({reason for sr in route_readiness.per_step for reason in sr.open_obligations})
    )


# --- PROCESS_SPECIFIED: the isopentyl positive + the guards that keep it honest -----------------

def test_isopentyl_acetate_reaches_process_specified():
    step = _isopentyl_acetate_step()
    readiness = evaluate_step(step)
    assert readiness.reaction_type is ObligationStatus.SATISFIED
    assert readiness.conditions is ObligationStatus.SATISFIED
    assert readiness.process is ObligationStatus.SATISFIED
    assert readiness.workup_isolation is ObligationStatus.SATISFIED
    assert readiness.tier == PROCESS_SPECIFIED  # the round's real, benign, sourced positive
    # the procedure's OWN accepted locator backs the process claim (never the envelope's conditions DOI)
    assert step.envelope.procedure is not None
    assert step.envelope.procedure.source_locator in readiness.provenance


def test_process_specified_stays_below_for_the_controls():
    # methyl salicylate (no procedure) and Diels-Alder (no declared conditions) never reach the top rung.
    for builder in (_methyl_salicylate_step, _paracetamol_anhydride_step, _diels_alder_step):
        readiness = evaluate_step(builder())
        assert readiness.tier != PROCESS_SPECIFIED


def test_completeness_predicate_reads_none_and_incomplete_evidence():
    from smartchem.decompiler_conditions import _ISOPENTYL_PROCEDURE
    from smartchem.procedure_evidence import EvidenceField

    assert procedure_representation_is_complete(None) is False
    assert procedure_representation_is_complete(_ISOPENTYL_PROCEDURE) is True
    # blank out one required whole-procedure field -> incomplete, even though the object is well-formed.
    import dataclasses

    gutted = dataclasses.replace(_ISOPENTYL_PROCEDURE, purification=EvidenceField.unknown())
    assert procedure_representation_is_complete(gutted) is False


def test_workup_gate_blocks_process_specified_when_workup_unsatisfied():
    # M18 (plan D4): even with reaction_type/conditions/process all SATISFIED, an UNSATISFIED workup caps the
    # tier at CONDITIONS_SUPPORTED. The tier @property enforces this by construction over the closed enum.
    r = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED,
        reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="acyl condensation (esterification/amidation)",
        conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.SATISFIED,
        workup_isolation=ObligationStatus.UNSATISFIED,
        provenance=("https://example.org/x",),
        open_obligations=(),
    )
    assert r.tier == CONDITIONS_SUPPORTED


def test_a_complete_but_unsourced_procedure_is_not_process_satisfied():
    # M13/M17: completeness alone never earns process/workup -- the accepted-source conjunct is mandatory.
    import dataclasses

    from smartchem.decompiler_conditions import _ISOPENTYL_PROCEDURE

    step = _isopentyl_acetate_step()
    unsourced = dataclasses.replace(_ISOPENTYL_PROCEDURE, source=None)
    envelope = dataclasses.replace(step.envelope, procedure=unsourced)
    stripped = dataclasses.replace(step, envelope=envelope)
    readiness = evaluate_step(stripped)
    assert procedure_representation_is_complete(unsourced) is True  # still structurally complete
    assert readiness.process is ObligationStatus.UNSATISFIED         # ... but not sourced -> not SATISFIED
    assert readiness.workup_isolation is ObligationStatus.UNSATISFIED
    assert readiness.tier == CONDITIONS_SUPPORTED


def test_step_readiness_and_route_readiness_are_digestible_and_stable():
    step = _methyl_salicylate_step()
    a = evaluate_step(step)
    b = evaluate_step(step)
    assert a.digest == b.digest  # same facts in, same digest out -- no hidden nondeterminism
    route_readiness_a = RouteReadiness(per_step=(a,), route_open_obligations=a.open_obligations)
    route_readiness_b = RouteReadiness(per_step=(b,), route_open_obligations=b.open_obligations)
    assert route_readiness_a.digest == route_readiness_b.digest


def test_step_readiness_rejects_an_orphaned_reaction_class_name():
    # a class name without SATISFIED, or SATISFIED without a class name, is an incoherent record --
    # M11's collapse-the-orthogonality mutant would produce exactly this shape, so the constructor refuses it.
    import pytest

    with pytest.raises(ValueError):
        StepReadiness(
            formal_candidate=ObligationStatus.SATISFIED,
            reaction_type=ObligationStatus.UNSATISFIED,
            reaction_class_name="acyl condensation (esterification/amidation)",
            conditions=ObligationStatus.UNKNOWN,
            process=ObligationStatus.UNKNOWN,
            workup_isolation=ObligationStatus.UNKNOWN,
            provenance=(),
            open_obligations=("reaction_type: not recognized by the production oracle",),
        )


def test_step_readiness_rejects_a_non_satisfied_base_rung():
    # Wave C / d'Alembert: the tier @property does not branch on formal_candidate, so without a base-rung guard a
    # direct constructor could mint formal_candidate=UNSATISFIED alongside a strong tier (tier would return
    # PROCESS_SPECIFIED off an UNSATISFIED base). __post_init__ is the module's declared anti-laundering guard, so it
    # must refuse this. A StepReadiness is only ever built for a conservation-certified step -> base rung is invariant.
    import pytest

    with pytest.raises(ValueError, match="formal_candidate must be SATISFIED"):
        StepReadiness(
            formal_candidate=ObligationStatus.UNSATISFIED,
            reaction_type=ObligationStatus.SATISFIED,
            reaction_class_name="acyl condensation (esterification/amidation)",
            conditions=ObligationStatus.SATISFIED,
            process=ObligationStatus.SATISFIED,
            workup_isolation=ObligationStatus.UNSATISFIED,
            provenance=(),
            open_obligations=(),
        )
