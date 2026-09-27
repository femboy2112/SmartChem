"""CLI-CAN-02 brick 2: APPLY the section-11 T/P constraint + populate ``ranked_route_dossiers``.

The typed response now ranks the search's routes against the declared bench box and carries a thin, digestible
:class:`~smartchem.service.RankedRouteSummary` per route -- the fit disposition (FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED)
with exact reasons, the READY-TIER-01 readiness floor, and the ranking's sourced verdicts.  The constraint rides the
search identity (brick 1) AND is now applied (brick 2); the disclosure flips from DECLARED to APPLIED, honestly, on
BOTH the recompile service and the ``compile`` dossier -- one constraint, one way (alias coherence).
"""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.compilation_ir import recompile_to_ir
from smartchem.data.reagents import commodity_inventory
from smartchem.experiment.drafter import ConstraintBox, fit_route
from smartchem.experiment.readiness import ObligationStatus, RouteReadiness, StepReadiness
from smartchem.experiment.routes import search_routes
from smartchem.service import (
    COMPILATION_RESPONSE_SCHEMA,
    CompilationResponse,
    RankedRouteSummary,
    RANKED_ROUTE_SUMMARY_SCHEMA,
    ResponseOutcome,
    _fit_counts,
    build_recompile_request,
    constraint_note,
    deserialize_response,
    ranked_summary_from_payload,
    ranked_summary_to_payload,
    run_compilation,
    serialize_response,
)
from smartchem.constraints import PhysicalBounds
from smartchem.structure import structure_by_name


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _routes(name="dimethyl ether"):
    """A real, non-empty route set for ``name`` (with commodity terminals, exactly as the service searches)."""
    m = structure_by_name(name).molecule.canonical()
    w = structure_by_name("water").molecule.canonical()
    comm = tuple(x.canonical() for x in commodity_inventory())
    res = search_routes(m, reagents=(w,), commodities=comm, max_depth=3, max_routes=100, cut_budget=20_000)
    assert res.routes, f"{name} must yield at least one route for these tests"
    return m, w, comm, res


# -- A. the RankedRouteSummary type: a coherent, digestible, serializable projection --------------------------------


def _formal_candidate_readiness() -> RouteReadiness:
    """A one-step ``RouteReadiness`` at the FORMAL_CANDIDATE floor -- an unrecognized reaction, no declared
    conditions/process/workup -- matching exactly what ``evaluate_step`` produces for a bare, fact-free step (v0.8
    Real Route Dossiers: this is the ladder's honest bottom rung, not a hard-coded stamp)."""
    open_obligations = (
        "conditions: no declared condition envelope (unknown)",
        "process: no declared process requirements (unknown)",
        "reaction_type: not recognized by the production oracle",
        "workup_isolation: no declared process requirements (unknown)",
    )
    step = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.UNSATISFIED,
        reaction_class_name=None, conditions=ObligationStatus.UNKNOWN, process=ObligationStatus.UNKNOWN,
        workup_isolation=ObligationStatus.UNKNOWN, provenance=(), open_obligations=open_obligations,
    )
    return RouteReadiness(per_step=(step,), route_open_obligations=open_obligations)


class TestRankedRouteSummaryType:
    def _valid(self, **over):
        base = dict(
            schema_version=RANKED_ROUTE_SUMMARY_SCHEMA, route_digest="d" * 64, equation="A -> B",
            fit_status="UNCONSTRAINED", readiness=_formal_candidate_readiness(), exclusions=(), gaps=(),
            composability_verdict="COMPOSABLE", selectivity_verdict="NOT_APPLICABLE",
            feasibility_verdict="FAVORABLE", equilibrium_verdict="BALANCED", kinetics_verdict="UNKNOWN",
            process_requirements=(),
        )
        base.update(over)
        return RankedRouteSummary(**base)

    def test_a_valid_summary_constructs_and_digests(self):
        s = self._valid()
        assert s.digest and s.digest == self._valid().digest
        assert s.readiness_tier == "FORMAL_CANDIDATE"   # derived, off the same readiness both instances share

    def test_bad_schema_version_is_refused(self):
        with pytest.raises(ValueError, match="schema_version"):
            self._valid(schema_version="wrong")

    def test_an_unknown_fit_status_is_refused(self):
        with pytest.raises(ValueError, match="fit_status"):
            self._valid(fit_status="MAYBE")

    def test_readiness_must_be_a_route_readiness(self):
        # v0.8 Real Route Dossiers: readiness_tier is retired as a settable field (self-promotion is now structurally
        # impossible -- there is no string to hand-pick) -- the constructor takes a typed RouteReadiness, and refuses
        # anything else. Its OWN construction (RouteReadiness/StepReadiness.__post_init__) is what stops a self-promote.
        with pytest.raises(TypeError, match="readiness"):
            self._valid(readiness="BENCH_DRAFT")

    def test_readiness_tier_is_no_longer_a_constructor_argument(self):
        base = dict(
            schema_version=RANKED_ROUTE_SUMMARY_SCHEMA, route_digest="d" * 64, equation="A -> B",
            fit_status="UNCONSTRAINED", readiness=_formal_candidate_readiness(), readiness_tier="FORMAL_CANDIDATE",
            exclusions=(), gaps=(), composability_verdict="COMPOSABLE", selectivity_verdict="NOT_APPLICABLE",
            feasibility_verdict="FAVORABLE", equilibrium_verdict="BALANCED", kinetics_verdict="UNKNOWN",
            process_requirements=(),
        )
        with pytest.raises(TypeError, match="readiness_tier"):
            RankedRouteSummary(**base)

    def test_excluded_must_give_a_reason(self):
        # the no-laundering discipline: an EXCLUDED route cannot hide WHY it was excluded.
        with pytest.raises(ValueError, match="EXCLUDED"):
            self._valid(fit_status="EXCLUDED", exclusions=())

    def test_a_fitting_route_cannot_carry_exclusions(self):
        # a disposition can never contradict its own reasons: FITS + an exclusion is incoherent.
        with pytest.raises(ValueError, match="FITS"):
            self._valid(fit_status="FITS", exclusions=("needs 900 K",))

    def test_a_nonstring_exclusion_is_refused(self):
        with pytest.raises(TypeError, match="exclusions"):
            self._valid(fit_status="EXCLUDED", exclusions=(123,))

    def test_payload_round_trip_is_identity(self):
        s = self._valid(fit_status="EXCLUDED", exclusions=("step 1: needs 900 K",), gaps=("step 2: T undeclared",))
        assert ranked_summary_from_payload(ranked_summary_to_payload(s)) == s


# -- B. of_fit: faithful projection of a drafter RouteFit ----------------------------------------------------------


class TestOfFitProjection:
    def test_projects_an_excluded_fit_faithfully(self):
        _, _, _, res = _routes()
        # an empty available-reagent inventory excludes every step that needs a reagent -> a real EXCLUDED fit.
        fit = fit_route(res.routes[0], ConstraintBox(available_reagents=frozenset()))
        assert fit.status.value == "EXCLUDED" and fit.exclusions
        s = RankedRouteSummary.of_fit(fit)
        assert s.fit_status == "EXCLUDED"
        assert tuple(s.exclusions) == tuple(fit.exclusions)   # reasons preserved, not summarised away
        assert s.route_digest == res.routes[0].digest         # links back to the IR candidate
        # v0.8 Real Route Dossiers: readiness is RE-DERIVED from the route's own steps, not a hard-coded stamp -- it
        # is whatever evaluate_route honestly says for THIS route's un-sourced, undeclared step(s), and must agree
        # with the typed readiness object riding alongside it.
        from smartchem.experiment.readiness import evaluate_route
        assert s.readiness == evaluate_route(fit.route)
        assert s.readiness_tier == s.readiness.tier

    def test_projects_an_unconstrained_fit(self):
        _, _, _, res = _routes()
        fit = fit_route(res.routes[0], ConstraintBox())   # empty box: nothing to fit
        assert RankedRouteSummary.of_fit(fit).fit_status == "UNCONSTRAINED"


# -- C. search-once reuse: the IR and the ranking describe ONE search ----------------------------------------------


class TestSearchOnceReuse:
    def test_precomputed_result_matches_a_fresh_search(self):
        m, w, comm, res = _routes()
        fresh = recompile_to_ir(m, reagents=(w,), commodities=comm, max_depth=3, max_results=100, cut_budget=20_000)
        reused = recompile_to_ir(m, reagents=(w,), commodities=comm, max_depth=3, max_results=100,
                                 cut_budget=20_000, search_result=res)
        assert fresh.digest == reused.digest                                    # identical IR
        assert tuple(c.candidate_digest for c in fresh.candidates) == \
               tuple(c.candidate_digest for c in reused.candidates)

    def test_a_mode_mismatched_result_is_refused(self):
        m, w, comm, res = _routes()
        # res is a ROUTE search result (no .dags); packaging it under mode='dags' must be a loud TypeError, never a
        # silent foreign search.
        with pytest.raises(TypeError, match="dags"):
            recompile_to_ir(m, reagents=(w,), commodities=comm, mode="dags", search_result=res)


# -- D. the populated response: applied constraint, honest disposition ---------------------------------------------


class TestRankedDossiersInResponse:
    def test_routes_found_populates_ranked_unconstrained(self):
        r = run_compilation(build_recompile_request("dimethyl ether"))
        assert r.outcome.value == "ROUTES_FOUND"
        assert r.ranked_route_dossiers, "a routes-found response must populate ranked_route_dossiers"
        assert all(s.fit_status == "UNCONSTRAINED" for s in r.ranked_route_dossiers)  # no bench, nothing to fit
        assert all(s.route_digest for s in r.ranked_route_dossiers)

    def test_the_ranked_route_digests_match_the_ir_candidates(self):
        r = run_compilation(build_recompile_request("acetic anhydride"))
        cand_ids = {c.candidate_digest for c in r.compilation_ir.candidates}
        assert cand_ids and {s.route_digest for s in r.ranked_route_dossiers} == cand_ids

    def test_a_constraint_on_an_undeclared_dimension_is_unknown_not_a_pass(self):
        # the section-11 honesty: a T ceiling over a route whose step leaves temperature undeclared is a GAP
        # (UNKNOWN-fit), never a silent FITS.  The note says so.
        r = run_compilation(build_recompile_request("dimethyl ether", max_temperature_k=250.0))
        assert all(s.fit_status in ("UNKNOWN", "EXCLUDED") for s in r.ranked_route_dossiers)
        note = next(d for d in r.diagnostics if "section-11 constraint APPLIED" in d)
        assert "never a silent pass" in note and "T<=250 K" in note

    def test_unconstrained_emits_no_constraint_note(self):
        r = run_compilation(build_recompile_request("dimethyl ether"))
        assert not any("section-11 constraint" in d for d in r.diagnostics)


# -- E. result_digest folds the ranking; alias-collapse survives ---------------------------------------------------


class TestResultDigestFoldsRanking:
    def test_constraint_moves_the_result_digest(self):
        base = run_compilation(build_recompile_request("dimethyl ether"))
        hot = run_compilation(build_recompile_request("dimethyl ether", max_temperature_k=300.0))
        assert base.result_digest != hot.result_digest      # the applied constraint is part of the result identity

    def test_same_constraint_is_deterministic(self):
        a = run_compilation(build_recompile_request("dimethyl ether", max_temperature_k=300.0))
        b = run_compilation(build_recompile_request("dimethyl ether", max_temperature_k=300.0))
        assert a.result_digest == b.result_digest and a.ranked_route_dossiers == b.ranked_route_dossiers

    @pytest.mark.parametrize("name,smiles", [
        ("dimethyl ether", "smiles:COC"),
        ("acetic anhydride", "smiles:CC(=O)OC(C)=O"),
    ])
    def test_alias_collapse_survives_the_ranked_fold(self, name, smiles):
        # SVC-REQ-01 F1/F2 regression: with ranked_route_dossiers folded into result_digest, a name and its canonical
        # SMILES -- which share a semantic_digest -- MUST still produce byte-identical ranked summaries and result.
        a = run_compilation(build_recompile_request(name))
        b = run_compilation(build_recompile_request(smiles))
        assert a.ranked_route_dossiers == b.ranked_route_dossiers
        assert a.result_digest == b.result_digest

    def test_constrained_aliases_also_collapse(self):
        a = run_compilation(build_recompile_request("dimethyl ether", max_temperature_k=300.0))
        b = run_compilation(build_recompile_request("smiles:COC", max_temperature_k=300.0))
        assert a.result_digest == b.result_digest

    def test_round_trip_preserves_ranked_and_digest(self):
        r = run_compilation(build_recompile_request("acetic anhydride", max_temperature_k=400.0))
        back = deserialize_response(serialize_response(r))
        assert back.ranked_route_dossiers == r.ranked_route_dossiers
        assert back.result_digest == r.result_digest


# -- F. the ONE note authority + the fit tally --------------------------------------------------------------------


class TestConstraintNote:
    def test_unconstrained_has_no_note(self):
        assert constraint_note(PhysicalBounds.unconstrained(), fit_counts=(0, 0, 0)) is None

    def test_no_routes_ranked_is_declared_not_applied(self):
        # fit_counts=None is the honest "declared, nothing ranked" (no routes, or a path that does not rank -- DAG).
        note = constraint_note(PhysicalBounds.of(max_temperature_k=500.0), fit_counts=None)
        assert "DECLARED" in note and "no routes were ranked" in note and "APPLIED" not in note

    def test_applied_reports_the_real_tally(self):
        note = constraint_note(PhysicalBounds.of(max_temperature_k=500.0), fit_counts=(2, 1, 3))
        assert "APPLIED" in note and "2 FIT" in note and "1 EXCLUDED" in note and "3 UNKNOWN-fit" in note

    def test_fit_counts_reads_dispositions_structurally(self):
        _, _, _, res = _routes()
        excluded = RankedRouteSummary.of_fit(fit_route(res.routes[0], ConstraintBox(available_reagents=frozenset())))
        unconstr = RankedRouteSummary.of_fit(fit_route(res.routes[0], ConstraintBox()))
        assert _fit_counts((excluded, unconstr)) == (0, 1, 0)   # UNCONSTRAINED counts nowhere; EXCLUDED counts once


# -- G. alias coherence: compile applies the SAME box ---------------------------------------------------------------


class TestCompileAliasApplies:
    def test_compile_dossier_reports_applied(self):
        _, out, _ = _cli(["compile", "acetic anhydride", "--max-depth", "2", "--max-temp", "500"])
        assert "constraint APPLIED" in out and "T<=500 K" in out

    def test_compile_unconstrained_has_no_note(self):
        _, out, _ = _cli(["compile", "acetic anhydride", "--max-depth", "2"])
        assert "section-11 constraint" not in out

    def test_recompile_and_compile_both_apply(self):
        # both aliases surface an APPLIED section-11 note for the same flag -- one constraint, one way.
        _, rc, _ = _cli(["recompile", "acetic anhydride", "--max-depth", "2", "--max-temp", "500"])
        _, cc, _ = _cli(["compile", "acetic anhydride", "--max-depth", "2", "--max-temp", "500"])
        assert "constraint APPLIED" in rc and "constraint APPLIED" in cc


# -- H. red-team folds (b97256e review) -----------------------------------------------------------------------------


class TestRedTeamFolds:
    def test_min_pressure_over_undeclared_pressure_is_unknown_not_a_silent_fit(self):
        # HIGH fold: the min_pressure FLOOR lacked the undeclared-dimension gap the two ceilings have, so a route whose
        # step left pressure undeclared read as FITS -- a silent pass on a constrained dimension, and the "never a
        # silent pass" note then lied. A floor over an undeclared pressure must be UNKNOWN-fit (a gap), never FITS.
        r = run_compilation(build_recompile_request("acetic anhydride", min_pressure_atm=2.0))
        assert r.ranked_route_dossiers
        assert all(s.fit_status != "FITS" for s in r.ranked_route_dossiers)
        note = next(d for d in r.diagnostics if "section-11 constraint APPLIED" in d)
        assert "0 FIT" in note   # the honest tally: nothing was confirmed to fit an undeclared dimension

    def _summary(self, **over):
        base = dict(
            schema_version=RANKED_ROUTE_SUMMARY_SCHEMA, route_digest="d" * 64, equation="A -> B",
            fit_status="UNCONSTRAINED", readiness=_formal_candidate_readiness(), exclusions=(), gaps=(),
            composability_verdict="COMPOSABLE", selectivity_verdict="NOT_APPLICABLE",
            feasibility_verdict="FAVORABLE", equilibrium_verdict="BALANCED", kinetics_verdict="UNKNOWN",
            process_requirements=(),
        )
        base.update(over)
        return RankedRouteSummary(**base)

    @pytest.mark.parametrize("label,over", [
        ("unknown-without-gap", dict(fit_status="UNKNOWN")),                       # a silent pass hiding as UNKNOWN
        ("fits-with-gap", dict(fit_status="FITS", gaps=("step 1: T undeclared",))),   # a gap is not a pass
        ("unconstrained-with-gap", dict(fit_status="UNCONSTRAINED", gaps=("g",))),
        ("unknown-with-exclusion", dict(fit_status="UNKNOWN", gaps=("g",), exclusions=("e",))),
        ("unconstrained-with-exclusion", dict(exclusions=("e",))),
    ])
    def test_the_full_coherence_table_is_enforced(self, label, over):
        # MED fold: the guard only rejected EXCLUDED-without-reason and FITS-with-exclusion; the producer's full
        # invariant (a PASS carries neither gap nor exclusion; UNKNOWN carries a gap and no exclusion) is now enforced.
        with pytest.raises(ValueError):
            self._summary(**over)

    def test_an_unsearched_outcome_cannot_carry_ranked_dossiers(self):
        # MED fold: _check_outcome_coherence guarded affordability_frontier but not ranked_route_dossiers, so a
        # REFUSED/INVALID response (no IR, no search) could smuggle a dossier into result_digest.
        req = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="no search"):
            CompilationResponse(
                COMPILATION_RESPONSE_SCHEMA, req, ResponseOutcome.REFUSED, None, None,
                ("x",), (self._summary(),), (),
            )
