"""v0.8 Real Route Dossiers -- Writer 4's job: prove ``RouteDossier`` (the OLDER drafter dossier)
consumes the SAME shared readiness evaluator as the service transport, honestly, not a second engine.

The whole point: before this round, ``RouteDossier.readiness`` was a hard-coded ``FORMAL_CANDIDATE``
wall (``ProcedureReadiness.FORMAL_CANDIDATE``, always, no matter what the route actually carried).
These tests build REAL routes -- one hand-assembled with sourced conditions but no reaction centre
(the paracetamol-anhydride non-monotonic case the plan calls out: best-sourced, worst-recognized),
and one generator-derived via the PROMOTED default (certified-route-v07) algebra so it actually carries
a ``reaction_center`` and gets oracle-VOUCHED -- and check the dossier's derived tier/obligations/render
agree with ``smartchem.experiment.readiness.evaluate_route`` called directly on the same route.
"""
from __future__ import annotations

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.experiment.drafter import draft_route_dossier
from smartchem.experiment.readiness import (
    FORMAL_CANDIDATE,
    PROCESS_SPECIFIED,
    REACTION_VOUCHED,
    ObligationStatus,
    evaluate_route,
)
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
ACOH = parse_smiles("CC(=O)O")


def _sourced_env() -> ConditionEnvelope:
    # A REAL accepted SourceCitation (not just a free-text "provenance" string) -- ConditionEnvelope.
    # is_sourced needs an explicitly-accepted typed citation, not merely EXPERIMENTAL status, so this
    # is what actually earns the readiness "conditions" obligation SATISFIED (readiness.py's
    # _conditions_obligation reads envelope.is_sourced, not envelope.status).
    return ConditionEnvelope(
        temperature=Interval(295, 353, "K"),
        medium="aqueous, mild acid; volumetric",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="ACS teaching synthesis",
        source=SourceCitation("https://example.test/acs-teaching-synthesis", SourceReview.ACCEPTED),
    )


def _sourced_but_unrecognized_route() -> ExperimentRoute:
    """The paracetamol anhydride-acetylation step: hand-assembled, sourced conditions, NO
    ``reaction_center`` -- the plan's own non-monotonicity witness (best-sourced, worst-recognized).
    """
    return ExperimentRoute.of(ExperimentStep.assembling(
        PARA, (AMP, ANH), (PARA, ACOH), reagents=(ANH,), envelope=_sourced_env(),
    ))


def _da_holdout_route() -> ExperimentRoute:
    """A fresh Diels-Alder holdout target, decomposed under the PROMOTED default (certified-route-v07)
    algebra so the reconstructed step carries a real ``reaction_center`` and is oracle-vouched -- but no
    condition envelope was ever declared for it, so it stays REACTION_VOUCHED, not higher."""
    target = parse_smiles("CC1=CCCCC1")  # a fresh substituted DA-alkene holdout (test_v0_7_forcing_corpus twin)
    ets, complete = _CERTIFIED.enumerate(target, (), budget=100_000)
    assert complete
    da_edges = [e for e in ets if e.witness_kind.startswith("DIELS_ALDER")]
    assert da_edges, "expected at least one Diels-Alder witness under the certified profile"
    edge = da_edges[0].transform
    fragments = edge.products
    result = search_routes(target, reagents=(), available=fragments, registry=_CERTIFIED, max_depth=2)
    assert result.routes, "no route reconstructed under the certified registry"
    route = result.routes[0]
    assert recognize_reaction_type(route.steps[0]) is not None, "oracle did not vouch the generated step"
    return route


class TestRouteDossierReadinessAgreesWithSharedEvaluator:
    """No second readiness engine: whatever tier/obligations ``evaluate_route`` derives for a route is
    EXACTLY what ``RouteDossier.readiness``/``render()`` for that same route reports."""

    def test_sourced_but_unrecognized_route_stays_formal_candidate(self):
        route = _sourced_but_unrecognized_route()
        dossier = draft_route_dossier(route)
        expected = evaluate_route(route, identity_losses=())

        assert dossier.readiness == expected
        assert dossier.readiness_tier == FORMAL_CANDIDATE
        # the non-monotonic finding itself: conditions ARE satisfied, reaction_type is NOT -- so the
        # tier is capped at the weaker rung even though this step is the best-sourced in the corpus.
        step0 = dossier.readiness.per_step[0]
        assert step0.conditions is ObligationStatus.SATISFIED
        assert step0.reaction_type is not ObligationStatus.SATISFIED

    def test_da_holdout_route_is_reaction_vouched_but_conditions_unknown(self):
        route = _da_holdout_route()
        dossier = draft_route_dossier(route)
        expected = evaluate_route(route, identity_losses=())

        assert dossier.readiness == expected
        assert dossier.readiness_tier == REACTION_VOUCHED
        step0 = dossier.readiness.per_step[0]
        assert step0.reaction_type is ObligationStatus.SATISFIED
        assert step0.conditions is ObligationStatus.UNKNOWN

    def test_readiness_field_is_a_route_readiness_not_the_legacy_enum(self):
        from smartchem.experiment.readiness import RouteReadiness

        route = _sourced_but_unrecognized_route()
        dossier = draft_route_dossier(route)
        assert type(dossier.readiness) is RouteReadiness


class TestRouteDossierRender:
    """The rendered text has to actually SHOW a reader why the tier is what it is -- not just print a
    static disclaimer regardless of the route's real evidence."""

    def test_render_shows_derived_tier_and_disclaimer_below_process_specified(self):
        route = _sourced_but_unrecognized_route()
        text = draft_route_dossier(route).render()
        assert f"READINESS: {FORMAL_CANDIDATE}" in text
        assert "NOT a bench-ready procedure" in text
        assert f"< {PROCESS_SPECIFIED}" in text

    def test_render_exposes_open_obligations(self):
        route = _sourced_but_unrecognized_route()
        dossier = draft_route_dossier(route)
        text = dossier.render()
        assert "OPEN OBLIGATIONS" in text
        assert dossier.readiness.route_open_obligations, "fixture must actually have an open obligation"
        for reason in dossier.readiness.route_open_obligations:
            assert reason in text

    def test_render_distinguishes_vouched_route_from_formal_candidate(self):
        vouched_text = draft_route_dossier(_da_holdout_route()).render()
        formal_text = draft_route_dossier(_sourced_but_unrecognized_route()).render()
        assert f"READINESS: {REACTION_VOUCHED}" in vouched_text
        assert "reaction_type recognized" in vouched_text
        assert f"READINESS: {FORMAL_CANDIDATE}" in formal_text
        assert "reaction_type recognized" not in formal_text.split("OPEN OBLIGATIONS")[0]

    def test_render_shows_per_step_evidence_state(self):
        route = _da_holdout_route()
        text = draft_route_dossier(route).render()
        assert "PER-STEP READINESS" in text
        assert f"tier={REACTION_VOUCHED}" in text
        assert "conditions=UNKNOWN" in text
