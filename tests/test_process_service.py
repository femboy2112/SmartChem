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
    assert set(fit.admissible_route_digests) == {c.candidate_digest for c in fit.candidates}
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


def test_dag_mode_process_is_conservatively_assessed_not_silently_unassessed():
    """Item 5b: a DAG-mode compile with a process constraint no longer leaves it SILENTLY unassessed.

    DAG (convergent) routes are not linearly ranked, so process_selection_status stays UNASSESSED and nothing is
    formally admitted -- but the conservative serial-flattening gate (dag_process_fit) reports the SOUND lower bound
    on admission (how many DAGs fit even run serially) as a clearly-bounded diagnostic.  On a bench that covers the
    seeded paracetamol record, at least one DAG conservatively FITS.
    """
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=_PARA_BENCH, **_PARA_DAG))
    assert resp.process_selection_status == "UNASSESSED"     # DAGs are not formally admitted
    assert not resp.admissible_route_digests                 # ... and never appear in the admissible list
    note = _dag_note(resp)
    assert note is not None and "SOUND lower bound" in note
    assert "1 would FIT even run serially" in note           # the covering bench admits the seeded route serially


def test_dag_mode_conservative_fit_never_claims_more_than_it_proves():
    """The serial-flattening gate is SOUND (never a false FITS): a stricter bench reports fewer/zero sound fits.

    'quick' caps a step at 60 min and the seeded paracetamol floor is 84 min, so the serial gate cannot claim the
    route fits -- the note reports 0 sound fits, and the constraint is still not silently dropped.  A time-based
    non-fit is explicitly flagged as possibly over-conservative, never as a formal exclusion.
    """
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=ProcessBounds.quick(), **_PARA_DAG))
    assert resp.process_selection_status == "UNASSESSED"
    note = _dag_note(resp)
    assert note is not None
    assert "0 would FIT even run serially" in note
    assert "over-conservative" in note                       # honest about the serial-sum boundary


def test_dag_process_fit_is_sound_but_over_conservative_on_time():
    """dag_process_fit itself: unconstrained bounds -> UNCONSTRAINED; a serial-sum total-time cap can over-EXCLUDE.

    A genuinely convergent DAG (two branches join at the esterification) with each step declaring a 40-min floor sums
    to 120 min on a SERIAL flattening.  A 90-min total budget therefore EXCLUDES it on the serial gate -- the
    documented over-conservatism: a bench that overlaps the branches might fit a budget the serial sum exceeds.  The
    gate never fabricates a fit (unconstrained bounds give UNCONSTRAINED, not FITS), and the exclusion here is the time
    axis.
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
            process=requirements(elapsed_minutes=Interval(40, 40, "min")),
        )
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    dag = SynthesisDAG.of(
        step(acoh, (ald, ald, o2), (acoh, acoh)),   # branch 1: -> acetic acid
        step(etoh, (ethene, water), (etoh,)),        # branch 2: -> ethanol
        step(ea, (acoh, etoh), (ea, water)),         # join: genuinely convergent
    )
    assert dag_process_fit(dag, ProcessBounds.unconstrained()).status is ProcessFitStatus.UNCONSTRAINED
    capped = dag_process_fit(dag, ProcessBounds(max_total_minutes=90.0))
    assert capped.status is ProcessFitStatus.EXCLUDED
    assert any("elapsed" in e or "total" in e for e in capped.exclusions)


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
