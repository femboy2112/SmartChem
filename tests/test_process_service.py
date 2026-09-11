"""Integration controls use invented metadata, never experimental chemistry evidence."""
import secrets
from dataclasses import replace

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.experiment import routes
from smartchem.experiment.drafter import ConstraintBox, fit_route
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements
from smartchem.service import (
    TransformGrammar, build_recompile_request, deserialize_request, deserialize_response, request_to_payload,
    request_from_payload, response_from_payload, response_to_payload, run_compilation,
    serialize_request, serialize_response,
)


def requirements(**changes):
    return replace(ProcessRequirements(
        elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic software control; no experimental claim",
    ), **changes)


def request(**kwargs):
    return build_recompile_request("smiles:CC(=O)OC", max_depth=2,
                                   process=ProcessBounds.quick(), **kwargs)


def test_process_profile_is_semantic_and_round_trips():
    req = request()
    assert deserialize_request(serialize_request(req)).semantic_digest == req.semantic_digest
    other = replace(req, constraints=replace(req.constraints, process=ProcessBounds.low_touch()))
    assert other.semantic_digest != req.semantic_digest


@pytest.mark.parametrize("mutation", ["missing", "extra", "nan", "enum"])
def test_invalid_process_payload_cannot_silently_drop_constraints(mutation):
    payload = request_to_payload(request())
    process = payload["constraints"]["process"]
    if mutation == "missing":
        del process["max_step_minutes"]
    elif mutation == "extra":
        process["pretend_unknown_fits"] = True
    elif mutation == "nan":
        process["max_step_minutes"] = float("nan")
    else:
        process["allowed_attention"] = ["EASY"]
    with pytest.raises((ValueError, TypeError)):
        request_from_payload(payload)


def test_real_catalog_unknown_process_is_neither_admitted_nor_cost_recommended():
    result = run_compilation(request())
    assert result.candidates
    assert result.process_selection_status == "NO_FIT_FOUND"
    assert result.exit_code == 5
    assert result.admissible_route_digests == result.affordability_frontier == ()
    assert all(r.fit_status == "UNKNOWN" for r in result.ranked_route_dossiers)
    assert deserialize_response(serialize_response(result)).result_digest == result.result_digest


def test_synthetic_declared_control_fits_real_search_and_workup_mutation_kills_it(monkeypatch):
    original = routes._conditions_for
    metadata = requirements()
    monkeypatch.setattr(routes, "_conditions_for", lambda t: replace(original(t), process=metadata))
    fit = run_compilation(request())
    assert fit.process_selection_status == "FITS_FOUND" and fit.exit_code == 0
    # Tension-A (ROUND 27): recompiling methyl acetate at depth 2 yields a 1-step route (no intermediate -> fits
    # under the synthetic process control) and a 2-step route whose C2H4O2 intermediate is a NON-acetic-acid isomer.
    # That intermediate no longer borrows acetic acid's stability record (a-reaction-key-by-formula-borrows-a-rate),
    # so the 2-step route carries a genuine COMPOSABILITY gap the synthetic PROCESS control cannot close, and is
    # correctly NOT admissible. The admissible set is therefore the FITS routes -- a NON-EMPTY PROPER subset of the
    # candidates -- and the excluded route is excluded for a composability (not a process) reason.
    admissible = set(fit.admissible_route_digests)
    candidate_digests = {c.candidate_digest for c in fit.candidates}
    assert admissible and admissible < candidate_digests
    assert admissible == {r.route_digest for r in fit.ranked_route_dossiers if r.fit_status == "FITS"}
    assert all(r.composability_verdict == "UNKNOWN" and r.fit_status == "UNKNOWN"
               for r in fit.ranked_route_dossiers if r.route_digest not in admissible)
    assert all(r.readiness_tier == "FORMAL_CANDIDATE" for r in fit.ranked_route_dossiers)
    metadata = replace(metadata, workup_included=False)
    gap = run_compilation(request())
    assert gap.exit_code == 5 and not gap.admissible_route_digests
    assert gap.result_digest != fit.result_digest


@pytest.mark.parametrize("field,forged", [
    ("process_selection_status", "FITS_FOUND"), ("admissible_route_digests", ["fabricated"]),
    ("exit_code", 0), ("result_digest", "fabricated"),
])
def test_derived_admission_fields_are_checked_when_loading(field, forged):
    payload = response_to_payload(run_compilation(request()))
    payload[field] = forged
    with pytest.raises(ValueError, match=field):
        response_from_payload(payload)


def test_nonexistent_or_duplicate_ranked_routes_cannot_be_admitted():
    result = run_compilation(request())
    first = result.ranked_route_dossiers[0]
    forged = replace(first, route_digest="f" * 64, fit_status="FITS", gaps=(), exclusions=())
    with pytest.raises(ValueError, match="returned IR candidate"):
        replace(result, ranked_route_dossiers=(forged,))
    with pytest.raises(ValueError, match="unique"):
        replace(result, ranked_route_dossiers=(first, first))


def test_imported_frontier_cannot_bypass_process_admission():
    restricted = run_compilation(request())
    donor = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    assert donor.affordability_frontier
    with pytest.raises(ValueError, match="only admitted FITS"):
        replace(restricted, affordability_frontier=donor.affordability_frontier)


def test_deserialized_admission_is_re_derived_not_blindly_trusted():
    """PROCESS-ADMIT-01: a route's ``fit_status`` is RE-DERIVED from its carried evidence, not trusted.

    Each ranked route now carries its per-step ``process_requirements``, so
    ``_check_process_admission_coherence`` re-runs ``evaluate_process_requirements`` at construction AND on load
    and refuses a ``fit_status`` the evidence cannot support.  The old LOCKSTEP forgery -- relabel a REAL UNKNOWN
    route to ``FITS`` and recompute the derived admissible/selection/exit fields -- is therefore REJECTED, because
    the untouched (undeclared) evidence still re-derives to ``UNKNOWN``.  Contrast
    test_nonexistent_or_duplicate_ranked_routes_cannot_be_admitted (a FAKE digest is caught by the membership
    guard) and test_admission_residual_needs_a_signature_to_close (the one remaining, documented, gap).
    """
    result = run_compilation(request())
    # Ground truth on the real catalog: every route is UNKNOWN; nothing is admitted.
    assert result.exit_code == 5 and not result.admissible_route_digests
    victim = result.ranked_route_dossiers[0]
    assert victim.fit_status == "UNKNOWN"

    # Relabel the disposition but leave the carried process evidence (undeclared -> re-derives to UNKNOWN).
    forged = replace(victim, fit_status="FITS", gaps=(), exclusions=())
    with pytest.raises(ValueError, match="re-derive"):
        replace(result, ranked_route_dossiers=(forged, *result.ranked_route_dossiers[1:]))

    # The same forgery smuggled through the JSON payload is refused on load, not silently admitted.
    payload = response_to_payload(result)
    payload["ranked_route_dossiers"][0]["fit_status"] = "FITS"
    payload["ranked_route_dossiers"][0]["gaps"] = []
    with pytest.raises(ValueError):
        response_from_payload(payload)


def test_key_holding_forger_residual_is_not_closable_by_a_signature():
    """The IRREDUCIBLE residual: a forger who runs in the producing process (or holds the key) still passes.

    A producer signature (COMBINED-VERDICT-AUTH, below) closes the KEYLESS out-of-band tamper -- an attacker who edits
    a serialized response without the key -- see test_signed_response_rejects_out_of_band_tamper.  What NO signature
    can close is a forger with the key: they build an internally coherent FITS-supporting response (relabel + fabricate
    matching ``process_requirements``) and then SIGN it, because a signature only proves "these bytes came from a
    key-holder unmodified", never "this verdict was honestly derived".  On the UNSIGNED path (no key) this forgery is
    accepted and round-trips -- that is the honest opt-in default: a deserialized admissible list is authoritative only
    from a trusted producer.  Pinned so the boundary stays explicit, never mistaken for a full authentication.
    """
    result = run_compilation(request())
    victim = result.ranked_route_dossiers[0]
    fabricated = (requirements(),) * len(victim.process_requirements)
    forged = replace(victim, fit_status="FITS", gaps=(), exclusions=(), process_requirements=fabricated)
    promoted = replace(result, ranked_route_dossiers=(forged, *result.ranked_route_dossiers[1:]))
    assert promoted.admissible_route_digests == (victim.route_digest,)
    assert promoted.exit_code == 0
    reloaded = deserialize_response(serialize_response(promoted))
    assert reloaded.admissible_route_digests == (victim.route_digest,)
    # A key-holding forger simply signs the lie, and a consumer requiring a signature accepts it -- irreducible.
    key = secrets.token_bytes(32)
    signed = serialize_response(promoted, signing_key=key)
    assert deserialize_response(signed, verification_key=key, require_signature=True).admissible_route_digests == (
        victim.route_digest,)


def test_non_process_axis_relabel_is_not_yet_authenticated(monkeypatch):
    """Boundary pin (evil-morty Finding 1): PROCESS-ADMIT-01 re-derives ONLY the process component.

    ``fit_status`` is the COMBINED verdict (composability + physical bounds + process).  A route EXCLUDED for a
    NON-process reason -- here a reaction over a physical temperature cap -- whose PROCESS evidence is FITS can
    still be bare-relabeled to FITS: the carried ``process_requirements`` re-derive to FITS, so
    ``_check_process_admission_coherence`` sees nothing wrong on its (process-only) axis.  Re-deriving the
    physical/reagent/equipment/composability axes in-band needs the per-step physical conditions and the full route
    graph the thin summary deliberately omits.  This test pins the UNSIGNED default (no verification key), where such a
    relabel is producer-declared and therefore accepted; the KEYLESS out-of-band form of exactly this tamper IS refused
    once the producer signs and the consumer requires a signature -- see test_signed_response_rejects_out_of_band_tamper
    (COMBINED-VERDICT-AUTH).  Pinned so no caller mistakes an UNSIGNED deserialized admissible list for an authenticated
    one.
    """
    from smartchem.contracts import EvidenceStatus
    declared = ProcessRequirements(
        elapsed_minutes=Interval(5, 10, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic control; no experimental claim",
    )
    hot = ConditionEnvelope(
        temperature=Interval(400, 400, "K"), status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic physical control; no experimental claim", process=declared,
    )
    monkeypatch.setattr(routes, "_conditions_for", lambda t: hot)
    result = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, process=ProcessBounds.quick(), max_temperature_k=350))
    victim = result.ranked_route_dossiers[0]
    assert victim.fit_status == "EXCLUDED"
    assert any("caps at 350" in e for e in victim.exclusions)  # excluded for a PHYSICAL reason, not a process one

    # Bare relabel: FITS, clear the text, leave process_requirements untouched (still process-FITS).
    forged = replace(victim, fit_status="FITS", exclusions=(), gaps=())
    assert forged.process_requirements == victim.process_requirements
    promoted = replace(result, ranked_route_dossiers=(forged, *result.ranked_route_dossiers[1:]))
    # ACCEPTED on the UNSIGNED path: the physical axis is not re-derived in-band (producer-declared default).
    assert promoted.admissible_route_digests == (victim.route_digest,)
    assert deserialize_response(serialize_response(promoted)).admissible_route_digests == (victim.route_digest,)


def test_producer_signature_round_trips_and_enforces_the_key():
    """COMBINED-VERDICT-AUTH mechanics: sign is opt-in, verify checks the key, misconfiguration is loud.

    The default (no key) is byte-identical to the unsigned form -- ``producer_signature`` is ``null`` -- so every
    existing caller and golden fixture is untouched.  A signed response verifies under the same key, is refused under
    a different key, and ``require_signature`` refuses an unsigned payload (and refuses to run without a key at all).
    """
    result = run_compilation(request())
    assert response_to_payload(result)["producer_signature"] is None  # opt-in: unsigned by default
    key, other = secrets.token_bytes(32), secrets.token_bytes(32)

    signed = serialize_response(result, signing_key=key)
    assert deserialize_response(signed, verification_key=key).result_digest == result.result_digest
    with pytest.raises(ValueError, match="does not verify"):
        deserialize_response(signed, verification_key=other)
    with pytest.raises(ValueError, match="required but the payload is unsigned"):
        deserialize_response(serialize_response(result), verification_key=key, require_signature=True)
    with pytest.raises(ValueError, match="require_signature needs a verification_key"):
        deserialize_response(signed, require_signature=True)


def test_signed_response_rejects_out_of_band_tamper(monkeypatch):
    """COMBINED-VERDICT-AUTH: a KEYLESS out-of-band relabel is refused -- even on an axis PROCESS-ADMIT-01 cannot re-derive.

    This is the close for test_non_process_axis_relabel_is_not_yet_authenticated's residual, for the one threat a
    signature can actually address: an attacker who edits a serialized response WITHOUT the producer key.  Here a route
    is EXCLUDED for a PHYSICAL reason (a temperature cap the process re-derivation never inspects); the attacker
    relabels it to ``FITS`` coherently (so the round-trip digest check still passes) but cannot re-sign, so the HMAC
    over the recomputed ``result_digest`` diverges from the stale signature they copied, and verification refuses it.
    The UNSIGNED path stays unchanged (the opt-in default); only the key-holding forger
    (test_key_holding_forger_residual_is_not_closable_by_a_signature) survives.
    """
    from smartchem.contracts import EvidenceStatus
    declared = ProcessRequirements(
        elapsed_minutes=Interval(5, 10, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True, provenance="synthetic control; no experimental claim",
    )
    hot = ConditionEnvelope(
        temperature=Interval(400, 400, "K"), status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic physical control; no experimental claim", process=declared,
    )
    monkeypatch.setattr(routes, "_conditions_for", lambda t: hot)
    result = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, process=ProcessBounds.quick(), max_temperature_k=350))
    victim = result.ranked_route_dossiers[0]
    assert victim.fit_status == "EXCLUDED"

    key = secrets.token_bytes(32)
    honest_payload = response_to_payload(result, signing_key=key)
    # The honest signed response verifies under the key.
    assert response_from_payload(honest_payload, verification_key=key,
                                 require_signature=True).result_digest == result.result_digest

    # A keyless attacker relabels the physical-axis exclusion to FITS out-of-band and keeps the stale signature.
    forged = replace(victim, fit_status="FITS", exclusions=(), gaps=())
    promoted = replace(result, ranked_route_dossiers=(forged, *result.ranked_route_dossiers[1:]))
    tampered = response_to_payload(promoted)  # coherent, self-consistent result_digest
    tampered["producer_signature"] = honest_payload["producer_signature"]  # the only signature they have seen
    with pytest.raises(ValueError, match="does not verify"):
        response_from_payload(tampered, verification_key=key, require_signature=True)
    # Unsigned, it is still accepted -- the opt-in default is unchanged.
    assert deserialize_response(serialize_response(promoted)).admissible_route_digests == (victim.route_digest,)


_PARA_DAG = dict(helper_reagents=("acetic acid",),
                 stock_materials=("4-aminophenol", "acetic anhydride"), max_depth=1)
_PARA_BENCH = ProcessBounds(
    allowed_attention=(Attention.PERIODIC,), allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
    available_equipment=("erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                         "fluted filter paper", "buchner funnel", "water aspirator"),
)


def _dag_note(resp):
    return next((d for d in resp.diagnostics if "DAG mode" in d), None)


def test_dag_mode_process_is_formally_admitted_not_left_unassessed():
    """DAG-ADMIT-01 (ROUND-13, supersedes ROUND-12's diagnostic-only close): a DAG-mode compile with a process
    constraint is FORMALLY admitted on the process axis -- process_selection_status flips off UNASSESSED.

    Each convergent DAG carries a RankedDAGSummary (in ranked_dag_dossiers) whose fit_status is the SOUND COMBINED
    dag_bench_fit verdict (DAG-BENCH-01: composability + physical + process).  The seeded paracetamol record is a
    single-step DAG (NO_TRANSITIONS composability, within the bench box), so its combined fit reduces to the process
    axis and soundly FITS, so process_selection_status is FITS_FOUND.  The DAG dossiers are a DISTINCT admission from
    linear routes -- they never enter admissible_route_digests (the linear combined-fit list); they enter the parallel
    admissible_dag_digests instead.
    """
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=_PARA_BENCH, **_PARA_DAG))
    assert resp.process_selection_status == "FITS_FOUND"     # no longer UNASSESSED -- formally admitted
    assert not resp.admissible_route_digests                 # ... but a DAG is not in the LINEAR admissible list ...
    assert resp.admissible_dag_digests                       # ... it is in the parallel DAG combined-fit list
    assert resp.ranked_dag_dossiers                           # the formal per-DAG combined admissions
    assert any(d.fit_status == "FITS" for d in resp.ranked_dag_dossiers)
    note = _dag_note(resp)
    assert note is not None and "FORMALLY admitted" in note
    assert "1 FIT (serial-achievable" in note                # the covering bench admits the seeded route (combined)


def test_dag_mode_admission_re_derives_and_survives_round_trip():
    """The DAG admission is RE-DERIVED on load (the convergent PROCESS-ADMIT-01 close), not trusted from the payload.

    A serialize->deserialize round-trip reconstructs the dossiers and re-runs the coherence guard, and a relabel of a
    DAG's combined fit_status from a stricter verdict to FITS is REFUSED because the carried process_requirements+edges
    still re-derive the PROCESS COMPONENT to the stricter verdict (a forged admission).
    """
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=ProcessBounds.quick(), **_PARA_DAG))                 # 'quick' excludes the seeded DAG on a step cap
    assert resp.process_selection_status == "NO_FIT_FOUND"           # assessed, none combined-FITS -> not UNASSESSED
    assert resp.ranked_dag_dossiers and all(d.fit_status == "EXCLUDED" for d in resp.ranked_dag_dossiers)
    # a clean round-trip preserves the admission and re-derives it without complaint.
    back = deserialize_response(serialize_response(resp))
    assert back.process_selection_status == "NO_FIT_FOUND"
    assert back.result_digest == resp.result_digest
    # forge: relabel an EXCLUDED DAG to a COHERENT-looking FITS (clear BOTH exclusions and gaps so the __post_init__
    # coherence table passes) -> the load-time RE-DERIVATION still catches it, because the carried requirements+edges
    # re-derive the PROCESS component to EXCLUDED.  (Clearing only exclusions is caught one layer earlier, by the
    # FITS-cannot-carry-gaps rule.)  The exclusion here IS on the process axis, which is the re-derived one.
    payload = response_to_payload(resp)
    payload["ranked_dag_dossiers"][0]["fit_status"] = "FITS"
    payload["ranked_dag_dossiers"][0]["exclusions"] = []
    payload["ranked_dag_dossiers"][0]["gaps"] = []
    with pytest.raises(ValueError, match="re-derive"):
        response_from_payload(payload)


def _convergent_40min_dag():
    """A genuinely convergent DAG: two independent 40-min branches join at a third 40-min step.
    Serial flattening = 120 min; critical path (either branch -> join) = 80 min.

    An ethyl-chloride synthesis (NOT esterification): two branches (ethanol dehydration -> ethene;
    hydrogen chloride from the elements) join at the hydrochlorination.  None of the three steps is a
    P1.3 domain-guarded free-acid dehydrative acylation, so every node carries a real (non-UNKNOWN)
    group-derived ΔG -- the join and HCl branch are FAVORABLE, the dehydration BORDERLINE, so the
    worst-node rollup is BORDERLINE/BALANCED (the earlier ethyl-acetate fixture's esterification join is
    now correctly UNKNOWN under the guard, which would have made the rollup vacuously UNKNOWN)."""
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.dag import SynthesisDAG
    from smartchem.experiment.step import ExperimentStep
    from smartchem.smiles import parse_smiles
    ethanol, ethene, water, h2, cl2, hcl, etcl = (parse_smiles(s) for s in
        ("CCO", "C=C", "O", "[H][H]", "ClCl", "Cl", "CCCl"))

    def step(target, reactants, products):
        env = ConditionEnvelope(
            temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
            provenance="synthetic process control; no experimental claim",
            process=requirements(elapsed_minutes=Interval(40, 40, "min")),
        )
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    return SynthesisDAG.of(
        step(ethene, (ethanol,), (ethene, water)),   # branch 1: ethanol -> ethene + water (BORDERLINE)
        step(hcl, (h2, cl2), (hcl, hcl)),            # branch 2: H2 + Cl2 -> 2 HCl (FAVORABLE)
        step(etcl, (ethene, hcl), (etcl,)),          # join: ethene + HCl -> ethyl chloride (genuinely convergent)
    )


def test_dag_process_fit_uses_a_sound_critical_path_not_a_serial_sum():
    """ROUND-12: the DAG gate aggregates ELAPSED over the critical path, so it stops OVER-excluding a concurrent route.

    The convergent DAG has critical path 80 min (a branch + the join) and serial sum 120 min.  The verdict now depends
    on WHICH aggregate a budget can prove against, and each branch is sound:

    * unconstrained -> UNCONSTRAINED (never fabricates a fit);
    * 130-min total >= serial 120 -> FITS (serial-achievable, the sound FITS certificate);
    * 90-min total: serial 120 > 90 but critical-path 80 <= 90 -> UNKNOWN, not the old over-conservative EXCLUDED
      (fittable only if the branches overlap -- undeclared, so honestly unknown, never a silent pass);
    * 70-min total: critical-path floor 80 > 70 -> EXCLUDED (unfittable even with fully concurrent branches -- a
      strictly TIGHTER, still-sound exclude than the serial-sum would give).
    """
    from smartchem.experiment.dag import dag_process_fit
    from smartchem.process_constraints import ProcessFitStatus
    dag = _convergent_40min_dag()
    assert dag_process_fit(dag, ProcessBounds.unconstrained()).status is ProcessFitStatus.UNCONSTRAINED
    assert dag_process_fit(dag, ProcessBounds(max_total_minutes=130.0)).status is ProcessFitStatus.FITS
    middle = dag_process_fit(dag, ProcessBounds(max_total_minutes=90.0))
    assert middle.status is ProcessFitStatus.UNKNOWN                      # was EXCLUDED under the serial-sum gate
    assert any("concurrent" in g for g in middle.gaps)
    assert not middle.exclusions                                          # the honest UNKNOWN never fabricates an exclusion
    tight = dag_process_fit(dag, ProcessBounds(max_total_minutes=70.0))
    assert tight.status is ProcessFitStatus.EXCLUDED                      # critical-path floor 80 > 70: sound exclude
    assert any("critical-path" in e for e in tight.exclusions)


def test_unsearched_outcome_cannot_smuggle_a_dag_dossier():
    """evil-morty fold (DAG-ADMIT-01, Finding 1): an unsearched outcome (REFUSED/INVALID/INTERNAL, ir None) must carry
    NO ranked_dag_dossiers -- the __post_init__ membership check is gated on ir being present, so WITHOUT the
    outcome-coherence fence a fabricated ghost dossier (a route_digest identifying no candidate) could ride into
    result_digest.  This is the exact fence the linear ranked_route_dossiers already had."""
    from dataclasses import replace as _replace

    from smartchem.service import _invalid, _refused
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=_PARA_BENCH, **_PARA_DAG))
    dossier = next(d for d in resp.ranked_dag_dossiers if d.fit_status == "FITS")
    for base in (_invalid(resp.request, "control"), _refused(resp.request, "control")):
        with pytest.raises(ValueError, match="must carry no ranked_dag_dossiers"):
            _replace(base, ranked_dag_dossiers=(dossier,))


def test_combined_fits_dag_flips_exit_to_success_but_a_non_fit_dag_stays_refused():
    """DAG-BENCH-01 (inverts the ROUND-13 DAG-ADMIT-01 finding-2 guard): a convergent DAG is now assessed on the
    COMBINED section-11 bench fit, so a combined-FITS DAG in a complete (ROUTES_FOUND) search DOES flip exit to success
    -- it is a first-class bench-usable route, sound because dag_process_fit's FITS is serial-achievable by one operator.

    The retained guard: a DAG that is NOT combined-FITS must still stay EXIT_REFUSED, never over-claiming success on a
    partial admission.  Both are demonstrated on the reachable methyl-acetate DAG shape: its REAL dossiers are UNKNOWN
    (the seeded records leave elapsed undeclared), so the real response stays REFUSED; injecting one COHERENT
    combined-FITS dossier (its carried requirements genuinely re-derive the process component to FITS) flips it to 0."""
    from dataclasses import replace as _replace

    from smartchem.service import EXIT_REFUSED, EXIT_SUCCESS, RANKED_DAG_SUMMARY_SCHEMA, RankedDAGSummary
    box = ProcessBounds(max_total_minutes=1000.0)                       # constrains something; a declared step fits it
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=3, process=box))
    assert resp.outcome.value == "ROUTES_FOUND" and resp.compilation_ir.complete_within_bounds  # a COMPLETE search
    # GUARD: the real dossiers are UNKNOWN-fit (undeclared elapsed), so nothing is combined-admissible -> exit REFUSED.
    assert resp.ranked_dag_dossiers and not any(d.fit_status == "FITS" for d in resp.ranked_dag_dossiers)
    assert not resp.admissible_dag_digests and resp.exit_code == EXIT_REFUSED
    # CAPABILITY: a coherent combined-FITS DAG dossier now DOES admit and flip exit to success.
    real_candidate = resp.compilation_ir.candidates[0].candidate_digest
    fitting = RankedDAGSummary(
        RANKED_DAG_SUMMARY_SCHEMA, real_candidate, "control step",
        "FITS", (), (), (requirements(),), (),                          # one declared step, no edges -> re-derives FITS
    )
    admitted = _replace(resp, ranked_dag_dossiers=(fitting,))
    assert admitted.process_selection_status == "FITS_FOUND"            # the DAG is combined-admitted ...
    assert not admitted.admissible_route_digests                        # ... not in the LINEAR list ...
    assert admitted.admissible_dag_digests == (real_candidate,)         # ... but in the parallel DAG combined list ...
    assert admitted.exit_code == EXIT_SUCCESS                           # ... so a combined-FITS DAG IS a bench pass


def test_dag_bench_fit_combines_the_physical_axis_and_admits_a_physical_only_dag_mode_compile():
    """DAG-BENCH-01 gate widening: the DAG bench admission is built when the box constrains ANYTHING (physical OR
    process), not just process -- so a PHYSICAL-only DAG-mode compile is judged by the same combined standard a linear
    physical-only compile is.  Two levels:

    (a) unit: dag_bench_fit folds the per-step PHYSICAL box for a DAG exactly as a linear route -- a 300 K step is
        EXCLUDED under a 100 K bench cap (a hard temperature over-bound) and NOT excluded under a 1000 K cap.
    (b) integration: a physical-only DAG-mode run_compilation now BUILDS the dossiers (the widened gate), the process
        selection is NOT_REQUESTED (no process box), nothing enters the process-gated admissible_dag_digests, and the
        response round-trips with an unchanged result_digest.
    """
    from smartchem.experiment.drafter import dag_bench_fit
    dag = _convergent_40min_dag()                                        # three 300 K steps, genuinely convergent
    tight = dag_bench_fit(dag, ConstraintBox(max_temperature_k=100.0))   # 300 K > 100 K cap -> a hard physical exclude
    assert tight.status.value == "EXCLUDED" and any("K" in e for e in tight.exclusions)
    loose = dag_bench_fit(dag, ConstraintBox(max_temperature_k=1000.0))  # 300 K <= 1000 K -> no temperature exclusion
    assert loose.status.value != "EXCLUDED" and not any("bench caps" in e for e in loose.exclusions)
    # (b) the widened gate builds dossiers for a physical-only DAG-mode compile (no process box at all).
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=3,
        max_temperature_k=1000.0))                                       # PHYSICAL-only: a T cap, no process bounds
    assert resp.ranked_dag_dossiers                                      # built despite no process box (the gate widened)
    assert all(d.fit_status in ("FITS", "EXCLUDED", "UNKNOWN", "UNCONSTRAINED") for d in resp.ranked_dag_dossiers)
    assert resp.process_selection_status == "NOT_REQUESTED"             # no process box -> not a process selection
    assert not resp.admissible_dag_digests                             # ... so the process-gated combined list is empty
    back = deserialize_response(serialize_response(resp))               # a coherent round-trip preserves the admission
    assert back.result_digest == resp.result_digest and back.ranked_dag_dossiers == resp.ranked_dag_dossiers


def test_dag_active_time_stays_serial_a_single_operator_does_not_parallelize():
    """ROUND-12 soundness crux: ACTIVE (hands-on) time is serial-summed even on a DAG.

    One operator cannot do two branches' hands-on work at the same moment, so parallelizing active time would be an
    UNSOUND relaxation (unlike elapsed wall-clock, which genuinely overlaps).  A convergent DAG whose three 40-min-
    ACTIVE steps serial-sum to 120 min is therefore EXCLUDED at a 90-min ACTIVE budget -- NOT relaxed to the 80-min
    critical path.  (Contrast the sibling test: the SAME shape's ELAPSED at a 90-min total is only UNKNOWN, because
    wall-clock does overlap.)
    """
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.dag import SynthesisDAG, dag_process_fit
    from smartchem.experiment.step import ExperimentStep
    from smartchem.process_constraints import ProcessFitStatus
    from smartchem.smiles import parse_smiles
    acoh, etoh, ea, water, ald, ethene, o2 = (parse_smiles(s) for s in
        ("CC(=O)O", "CCO", "CC(=O)OCC", "O", "CC=O", "C=C", "O=O"))

    def step(target, reactants, products):
        env = ConditionEnvelope(
            temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
            provenance="synthetic process control; no experimental claim",
            process=requirements(elapsed_minutes=Interval(40, 40, "min"), active_minutes=Interval(40, 40, "min")),
        )
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    dag = SynthesisDAG.of(
        step(acoh, (ald, ald, o2), (acoh, acoh)),
        step(etoh, (ethene, water), (etoh,)),
        step(ea, (acoh, etoh), (ea, water)),
    )
    # ELAPSED at a 90-min TOTAL is only UNKNOWN (wall-clock overlaps: critical path 80 <= 90 < serial 120) ...
    elapsed_view = dag_process_fit(dag, ProcessBounds(max_total_minutes=90.0))
    assert elapsed_view.status is ProcessFitStatus.UNKNOWN
    # ... but ACTIVE at the SAME 90 is EXCLUDED: hands-on time is serial-summed (120 > 90), never relaxed to 80.
    fit = dag_process_fit(dag, ProcessBounds(max_active_minutes=90.0))
    assert fit.status is ProcessFitStatus.EXCLUDED
    assert any("active" in e for e in fit.exclusions)


@pytest.mark.parametrize("field,value,bounds", [
    ("peak_temperature_k", 500, PhysicalBounds.of(max_temperature_k=350)),
    ("max_pressure_atm", 5, PhysicalBounds.of(max_pressure_atm=2)),
    ("min_pressure_atm", 0.1, PhysicalBounds.of(min_pressure_atm=0.5)),
])
def test_workup_extrema_override_mild_reaction_conditions(field, value, bounds):
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.step import ExperimentRoute, ExperimentStep
    from smartchem.identity_parse import resolve_target
    water = resolve_target("water")
    # Conserving identity control isolates admission; no synthesis claim.
    def route(metadata):
        envelope = ConditionEnvelope(temperature=Interval(300, 300, "K"),
            pressure=Interval(1, 1, "atm"), status=EvidenceStatus.EXPERIMENTAL,
            provenance="synthetic physical control", process=metadata)
        return ExperimentRoute.of(ExperimentStep.assembling(water, (water,), (water,), envelope=envelope))
    box = ConstraintBox.of_bounds(bounds, process=ProcessBounds.quick())
    unknown = fit_route(route(requirements()), box)
    assert any("whole-process" in gap and field in gap for gap in unknown.gaps)
    excluded = fit_route(route(requirements(**{field: value})), box)
    assert any("whole-process" in reason and field in reason for reason in excluded.exclusions)


@pytest.mark.parametrize("field,interval", [
    ("temperature", Interval(-10, -5, "K")),
    ("pressure", Interval(-1, 0, "atm")),
    ("duration", Interval(-10, -5, "min")),
])
def test_invalid_declared_conditions_are_rejected_at_construction(field, interval):
    from smartchem.contracts import EvidenceStatus
    with pytest.raises(ValueError):
        ConditionEnvelope(**{field: interval}, status=EvidenceStatus.EXPERIMENTAL,
                          provenance="malformed control")
